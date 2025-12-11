"""Main calendar generation orchestrator."""

from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional, Tuple

from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
    WeeklyCalendar,
    EvaluationReport,
    PostingHistoryEntry,
    ContentIdea,
)
from src.planning.pillars import derive_content_pillars
from src.planning.targets import build_weekly_target, validate_target_feasibility
from src.planning.ideas import generate_candidate_ideas
from src.planning.selection import select_weekly_actions
from src.planning.prompts import generate_prompt_brief
from src.evaluation.evaluator import evaluate_calendar


def generate_content_calendar(
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
    templates: List[ChatGPTQueryTemplate],
    num_posts_per_week: int,
    history: List[PostingHistoryEntry],
    week_index: int,
    start_date: Optional[datetime] = None,
    use_llm: bool = True,
    debug_timing: bool = False,
) -> Tuple[WeeklyCalendar, EvaluationReport]:
    """Generate a weekly content calendar.
    
    This is the main entry point that orchestrates the full pipeline:
    1. Derive content pillars from company info
    2. Build weekly target distribution
    3. Generate candidate content ideas
    4. Score and select the best ideas
    5. Generate prompt briefs for each action
    6. Evaluate the final calendar
    
    Args:
        company: Company information
        personas: Available personas (2+)
        subreddits: Target subreddits
        templates: ChatGPT query templates
        num_posts_per_week: Target number of actions
        history: Past posting history (for de-duplication)
        week_index: Which week to generate (1-indexed)
        start_date: Optional start date for the week
        debug_timing: If True, print timing information for each step
        
    Returns:
        Tuple of (WeeklyCalendar, EvaluationReport)
    """
    total_start = time.time()
    
    # Step 1: Derive content pillars
    if debug_timing:
        step_start = time.time()
        print(f"\n[DEBUG] Step 1: Derive content pillars...")
    
    pillars = derive_content_pillars(company)
    
    if debug_timing:
        print(f"[DEBUG]   → {len(pillars)} pillars in {time.time() - step_start:.3f}s")
    
    # Step 2: Build weekly target (with pillar rotation based on history)
    if debug_timing:
        step_start = time.time()
        print(f"[DEBUG] Step 2: Build weekly target...")
    
    weekly_target = build_weekly_target(
        num_posts_per_week=num_posts_per_week,
        personas=personas,
        subreddits=subreddits,
        pillars=pillars,
        history=history,
    )
    
    # Validate feasibility of the target
    feasibility_warnings = validate_target_feasibility(weekly_target, personas, subreddits)
    
    if debug_timing:
        print(f"[DEBUG]   → Target built in {time.time() - step_start:.3f}s")
        if feasibility_warnings:
            for w in feasibility_warnings:
                print(f"[DEBUG]   ⚠️ {w}")
    
    # Step 3: Generate candidate ideas
    if debug_timing:
        step_start = time.time()
        print(f"[DEBUG] Step 3: Generate candidate ideas (use_llm={use_llm})...")
    
    candidates = generate_candidate_ideas(
        company=company,
        personas=personas,
        subreddits=subreddits,
        templates=templates,
        pillars=pillars,
        history=history,
        use_llm=use_llm,
        debug_timing=debug_timing,
    )
    
    if debug_timing:
        print(f"[DEBUG]   → {len(candidates)} candidates in {time.time() - step_start:.3f}s")
    
    # Step 4: Score and select
    if debug_timing:
        step_start = time.time()
        print(f"[DEBUG] Step 4: Score and select actions...")
    
    actions = select_weekly_actions(
        candidates=candidates,
        weekly_target=weekly_target,
        subreddits=subreddits,
        history=history,
        week_index=week_index,
        start_date=start_date,
        templates=templates,
    )
    
    if debug_timing:
        print(f"[DEBUG]   → {len(actions)} actions selected in {time.time() - step_start:.3f}s")
    
    # Step 5: Generate prompt briefs
    if debug_timing:
        step_start = time.time()
        print(f"[DEBUG] Step 5: Generate prompt briefs...")
    
    # Create a lookup for ideas by ID
    idea_lookup = {c.id: c for c in candidates}
    
    for action in actions:
        idea = idea_lookup.get(action.content_idea_id)
        if idea:
            # Denormalize key metadata onto the action for downstream consumers
            action.topic = idea.topic
            action.pillar_id = idea.pillar_id
            action.keyword_ids = list(getattr(idea, "keyword_ids", []) or [])
            action.prompt_brief = generate_prompt_brief(
                action=action,
                idea=idea,
                company=company,
                personas=personas,
                subreddits=subreddits,
            )
    
    if debug_timing:
        print(f"[DEBUG]   → {len(actions)} briefs in {time.time() - step_start:.3f}s")
    
    # Create the calendar
    calendar = WeeklyCalendar(
        week_index=week_index,
        company_id=company.id,
        actions=actions,
    )
    
    # Step 6: Evaluate
    if debug_timing:
        step_start = time.time()
        print(f"[DEBUG] Step 6: Evaluate calendar...")
    
    evaluation = evaluate_calendar(
        calendar=calendar,
        company=company,
        personas=personas,
        subreddits=subreddits,
        history=history,
    )
    
    # Add feasibility warnings to evaluation
    if feasibility_warnings:
        evaluation.warnings.extend(feasibility_warnings)
    
    # Add underfill warning if we couldn't meet the target
    if len(actions) < num_posts_per_week:
        underfill_warning = (
            f"Underfill: only {len(actions)} actions generated vs {num_posts_per_week} requested. "
            f"Check subreddit/persona capacities."
        )
        evaluation.warnings.append(underfill_warning)
        if debug_timing:
            print(f"[DEBUG]   ⚠️ {underfill_warning}")
    
    if debug_timing:
        print(f"[DEBUG]   → Evaluated in {time.time() - step_start:.3f}s")
        print(f"[DEBUG] TOTAL TIME: {time.time() - total_start:.3f}s\n")
    
    return calendar, evaluation


def calendar_to_history(calendar: WeeklyCalendar, ideas: List) -> List[PostingHistoryEntry]:
    """Convert a calendar's actions to history entries.
    
    Use this after a calendar is "executed" to add to history for next week.
    
    Args:
        calendar: The completed calendar
        ideas: List of ContentIdea objects (to look up topics and pillars)
        
    Returns:
        List of PostingHistoryEntry objects
    """
    idea_lookup = {i.id: i for i in ideas}
    entries = []
    
    for action in calendar.actions:
        idea = idea_lookup.get(action.content_idea_id)
        if idea:
            entries.append(PostingHistoryEntry(
                date=action.date,
                subreddit_name=action.subreddit_name,
                persona_id=action.persona_id,
                topic=idea.topic,
                pillar_id=idea.pillar_id,
                week_index=calendar.week_index,
            ))
    
    return entries


# CLI entry point for testing
if __name__ == "__main__":
    from src.config.slideforge import get_slideforge_config
    
    company, personas, subreddits, templates = get_slideforge_config()
    
    print(f"Generating calendar for {company.name}...")
    print(f"Personas: {[p.name for p in personas]}")
    print(f"Subreddits: {[s.name for s in subreddits]}")
    print()
    
    calendar, evaluation = generate_content_calendar(
        company=company,
        personas=personas,
        subreddits=subreddits,
        templates=templates,
        num_posts_per_week=10,
        history=[],
        week_index=1,
    )
    
    print(f"=== Week {calendar.week_index} Calendar ===")
    print(f"Total actions: {len(calendar.actions)}")
    print()
    
    for action in calendar.actions:
        print(f"{action.date} ({action.time_slot})")
        print(f"  Subreddit: {action.subreddit_name}")
        print(f"  Persona: {action.persona_id}")
        print(f"  Type: {action.post_type}")
        print(f"  Score: {action.quality_score:.1f}")
        print()
    
    print(f"=== Evaluation ===")
    print(f"Overall: {evaluation.overall_score:.1f}/10")
    print(f"Authenticity: {evaluation.authenticity_score:.1f}")
    print(f"Diversity: {evaluation.diversity_score:.1f}")
    print(f"Cadence: {evaluation.cadence_score:.1f}")
    print(f"Alignment: {evaluation.alignment_score:.1f}")
    
    if evaluation.warnings:
        print(f"Warnings: {evaluation.warnings}")

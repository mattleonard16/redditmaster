"""Convenience wrapper for generating next week's calendar."""

from __future__ import annotations

from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
    PostingHistoryEntry,
    WeeklyCalendar,
    EvaluationReport,
)
from src.planning.calendar import generate_content_calendar


def generate_next_week(
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
    templates: List[ChatGPTQueryTemplate],
    history: List[PostingHistoryEntry],
    num_posts_per_week: int = 10,
    start_date: Optional[datetime] = None,
    use_llm: bool = True,
) -> Tuple[WeeklyCalendar, EvaluationReport, List[PostingHistoryEntry]]:
    """Generate the next week's calendar based on existing history.
    
    This is the main entrypoint for:
    - "Generate Next Week" button in the UI
    - Future cron job automation
    
    Args:
        company: Company information
        personas: List of personas to use
        subreddits: Target subreddits
        templates: ChatGPT query templates
        history: All posting history so far
        num_posts_per_week: Target number of posts
        start_date: Optional start date (defaults to next Monday)
        
    Returns:
        Tuple of:
        - WeeklyCalendar for the new week
        - EvaluationReport with quality scores
        - Updated history including new actions
    """
    # Determine week index from history
    existing_weeks = {entry.week_index for entry in history}
    next_week_index = max(existing_weeks, default=0) + 1
    
    # Calculate start date if not provided
    if start_date is None:
        # Default to next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, start next Monday
        start_date = today + timedelta(days=days_until_monday)
    
    # Generate the calendar
    calendar, evaluation = generate_content_calendar(
        company=company,
        personas=personas,
        subreddits=subreddits,
        templates=templates,
        num_posts_per_week=num_posts_per_week,
        history=history,
        week_index=next_week_index,
        start_date=start_date,
        use_llm=use_llm,
    )
    
    # Convert actions to history entries for continuity
    # Extract topic from prompt_brief (first line after "Topic:") if available
    new_history = history.copy()
    for action in calendar.actions:
        # Try to extract topic from prompt_brief
        topic = _extract_topic_from_brief(action.prompt_brief)
        if not topic:
            topic = f"Action {action.content_idea_id[:8]}"
        
        # Try to infer pillar from post type and topic keywords
        pillar_id = _infer_pillar_from_topic(topic)
        
        new_history.append(PostingHistoryEntry(
            date=action.date,
            subreddit_name=action.subreddit_name,
            persona_id=action.persona_id,
            topic=topic,
            pillar_id=pillar_id,
            week_index=next_week_index,
        ))
    
    return calendar, evaluation, new_history


def _extract_topic_from_brief(prompt_brief: str) -> str:
    """Extract topic from a prompt brief."""
    if not prompt_brief:
        return ""
    
    # Look for "Topic:" line
    for line in prompt_brief.split("\n"):
        line = line.strip()
        if line.startswith("Topic:"):
            return line.replace("Topic:", "").strip()
    
    # Look for "about:" pattern
    if "about:" in prompt_brief.lower():
        idx = prompt_brief.lower().find("about:")
        topic_start = prompt_brief[idx + 6:].strip()
        # Take first sentence or line
        end = min(
            topic_start.find("\n") if "\n" in topic_start else len(topic_start),
            topic_start.find(".") if "." in topic_start else len(topic_start),
            80  # Max length
        )
        return topic_start[:end].strip()
    
    return ""


def _infer_pillar_from_topic(topic: str) -> str:
    """Infer pillar_id from topic keywords."""
    topic_lower = topic.lower()
    
    if any(w in topic_lower for w in ["struggling", "problem", "issue", "pain", "frustrated"]):
        return "problems"
    elif any(w in topic_lower for w in ["how to", "how do", "guide", "tutorial"]):
        return "howto"
    elif any(w in topic_lower for w in ["worked", "success", "finally", "solved"]):
        return "case_studies"
    elif any(w in topic_lower for w in ["compare", "vs", "versus", "better"]):
        return "comparisons"
    elif any(w in topic_lower for w in ["opinion", "think", "thoughts"]):
        return "opinions"
    else:
        return "problems"  # Default


def generate_multi_week(
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
    templates: List[ChatGPTQueryTemplate],
    num_weeks: int = 4,
    num_posts_per_week: int = 10,
    start_date: Optional[datetime] = None,
    use_llm: bool = True,
) -> List[Tuple[WeeklyCalendar, EvaluationReport]]:
    """Generate multiple weeks of calendars at once.
    
    Useful for planning ahead or batch generation.
    
    Args:
        company: Company information
        personas: List of personas
        subreddits: Target subreddits
        templates: ChatGPT query templates
        num_weeks: Number of weeks to generate
        num_posts_per_week: Posts per week
        start_date: Start date for week 1
        
    Returns:
        List of (WeeklyCalendar, EvaluationReport) tuples
    """
    results = []
    history: List[PostingHistoryEntry] = []
    current_date = start_date
    
    for week in range(1, num_weeks + 1):
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=num_posts_per_week,
            history=history,
            week_index=week,
            start_date=current_date,
            use_llm=use_llm,
        )
        
        results.append((calendar, evaluation))
        
        # Add to history for next iteration
        for action in calendar.actions:
            topic = _extract_topic_from_brief(action.prompt_brief)
            if not topic:
                topic = f"Week {week} action"
            pillar_id = _infer_pillar_from_topic(topic)
            
            history.append(PostingHistoryEntry(
                date=action.date,
                subreddit_name=action.subreddit_name,
                persona_id=action.persona_id,
                topic=topic,
                pillar_id=pillar_id,
                week_index=week,
            ))
        
        # Move to next week
        if current_date:
            current_date = current_date + timedelta(days=7)
    
    return results

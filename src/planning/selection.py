"""Selection algorithm for building the weekly calendar."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional

from src.models import (
    ContentIdea,
    PlannedAction,
    WeeklyTarget,
    PostingHistoryEntry,
    Subreddit,
    ChatGPTQueryTemplate,
)
from src.planning.scoring import score_idea


def select_weekly_actions(
    candidates: List[ContentIdea],
    weekly_target: WeeklyTarget,
    subreddits: List[Subreddit],
    history: List[PostingHistoryEntry],
    week_index: int,
    start_date: Optional[datetime] = None,
    templates: Optional[List["ChatGPTQueryTemplate"]] = None,
) -> List[PlannedAction]:
    """Select the best content ideas to form a weekly calendar.
    
    Uses a greedy algorithm that:
    1. Scores all candidates
    2. Iteratively picks the best candidate that doesn't violate quotas
    3. Assigns dates and time slots spread across the week
    
    Args:
        candidates: Pool of content ideas to choose from
        weekly_target: Target distribution and quotas
        subreddits: Subreddit configurations (for daily limits)
        history: Past posting history
        week_index: Which week this is for
        start_date: First day of the week (defaults to next Monday)
        
    Returns:
        List of planned actions for the week
    """
    if start_date is None:
        # Default to next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        start_date = today + timedelta(days=days_until_monday)
    
    actions: list[PlannedAction] = []
    
    # Track usage for quota enforcement
    subreddit_counts: dict[str, int] = {}
    persona_counts: dict[str, int] = {}
    pillar_counts: dict[str, int] = {}  # Now actually enforced!
    post_type_counts: dict[str, int] = {}  # Track post type diversity
    daily_subreddit_counts: dict[str, dict[str, int]] = {}  # date -> subreddit -> count
    
    # Build subreddit daily limits lookup
    subreddit_daily_limits = {s.name: s.max_posts_per_day for s in subreddits}
    
    # Build template lookup for scoring
    template_lookup = {}
    if templates:
        template_lookup = {t.id: t for t in templates}
    
    # Target post type distribution (40% new posts, 60% comments)
    target_new_posts = int(weekly_target.total_actions * weekly_target.new_post_share)
    
    # Track which candidates have been used
    used_idea_ids: set[str] = set()
    
    # Time slot rotation
    time_slots: list[Literal["morning", "afternoon", "evening"]] = [
        "morning", "afternoon", "evening"
    ]
    slot_index = 0
    
    while len(actions) < weekly_target.total_actions:
        # Calculate how many new posts we still need
        current_new_posts = post_type_counts.get("new_post", 0)
        need_more_new_posts = current_new_posts < target_new_posts
        
        # Score remaining candidates
        scored_candidates = []
        for candidate in candidates:
            if candidate.id in used_idea_ids:
                continue
            
            # Check if this candidate is eligible (doesn't violate hard quotas)
            if not _is_eligible(
                candidate,
                weekly_target,
                subreddit_counts,
                persona_counts,
                pillar_counts,
            ):
                continue
            
            # Get template for this idea (if available)
            template = template_lookup.get(candidate.template_id)
            
            score = score_idea(
                candidate,
                weekly_target,
                history,
                subreddit_counts,
                persona_counts,
                pillar_counts,
                template,
            )
            
            # Apply post type diversity bonus
            if need_more_new_posts and candidate.post_type == "new_post":
                score += 1.5  # Boost new posts when we need them
            elif not need_more_new_posts and candidate.post_type != "new_post":
                score += 0.5  # Slightly prefer comments when we have enough new posts
            
            # Penalize if we have too many of one type already
            type_count = post_type_counts.get(candidate.post_type, 0)
            if type_count >= len(actions) * 0.6 and len(actions) > 3:
                score -= 1.0  # Penalize overused post types
            
            # Ensure score stays in 0-10 range
            score = max(0.0, min(10.0, score))
            
            scored_candidates.append((score, candidate))
        
        if not scored_candidates:
            # No more eligible candidates
            break
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Pick the best candidate
        best_score, best_candidate = scored_candidates[0]
        used_idea_ids.add(best_candidate.id)
        
        # Assign date and time slot
        day_offset = len(actions) % 7  # Spread across 7 days
        action_date = start_date + timedelta(days=day_offset)
        date_str = action_date.strftime("%Y-%m-%d")
        
        time_slot = time_slots[slot_index % len(time_slots)]
        slot_index += 1
        
        # Check daily limit for this subreddit
        if date_str not in daily_subreddit_counts:
            daily_subreddit_counts[date_str] = {}
        
        daily_count = daily_subreddit_counts[date_str].get(best_candidate.subreddit_name, 0)
        daily_limit = subreddit_daily_limits.get(best_candidate.subreddit_name, 2)
        
        if daily_count >= daily_limit:
            # Try to find a different day for this subreddit
            for alt_offset in range(7):
                alt_date = start_date + timedelta(days=alt_offset)
                alt_date_str = alt_date.strftime("%Y-%m-%d")
                alt_daily = daily_subreddit_counts.get(alt_date_str, {}).get(
                    best_candidate.subreddit_name, 0
                )
                if alt_daily < daily_limit:
                    date_str = alt_date_str
                    action_date = alt_date
                    if date_str not in daily_subreddit_counts:
                        daily_subreddit_counts[date_str] = {}
                    break
        
        # Create the action
        action = PlannedAction(
            id=str(uuid.uuid4()),
            week_index=week_index,
            date=date_str,
            time_slot=time_slot,
            subreddit_name=best_candidate.subreddit_name,
            persona_id=best_candidate.persona_id,
            post_type=best_candidate.post_type,
            content_idea_id=best_candidate.id,
            prompt_brief="",  # Will be filled in by generate_prompt_brief
            quality_score=best_score,
            # Set thread_id for new posts to enable conversation threading
            thread_id=str(uuid.uuid4()) if best_candidate.post_type == "new_post" else None,
            parent_action_id=None,
        )
        actions.append(action)
        
        # Update counts
        subreddit_counts[best_candidate.subreddit_name] = (
            subreddit_counts.get(best_candidate.subreddit_name, 0) + 1
        )
        persona_counts[best_candidate.persona_id] = (
            persona_counts.get(best_candidate.persona_id, 0) + 1
        )
        pillar_counts[best_candidate.pillar_id] = (
            pillar_counts.get(best_candidate.pillar_id, 0) + 1
        )
        post_type_counts[best_candidate.post_type] = (
            post_type_counts.get(best_candidate.post_type, 0) + 1
        )
        daily_subreddit_counts[date_str][best_candidate.subreddit_name] = (
            daily_subreddit_counts[date_str].get(best_candidate.subreddit_name, 0) + 1
        )

    # Attach comments into plausible conversation threads.
    # This does NOT change the action count; it only sets thread_id/parent_action_id.
    _assign_threading(actions)

    # Sort by date and time slot for readability
    slot_order = {"morning": 0, "afternoon": 1, "evening": 2}
    actions.sort(key=lambda a: (a.date, slot_order.get(a.time_slot, 0)))
    
    return actions


# Note: Conversation threading (replies to our own posts) can be added as a 
# separate optional feature. The thread_id field on PlannedAction supports this.
# To enable: after generating the calendar, call add_conversation_replies()
# which schedules follow-up comments from different personas.


def _assign_threading(actions: List[PlannedAction]) -> None:
    """Link comment actions to earlier new posts to form believable threads.

    We preserve the scheduled dates/times (to keep constraint checks stable).
    Comments are only attached when they occur after an appropriate root post
    in the same subreddit.
    """
    if not actions:
        return

    slot_order = {"morning": 0, "afternoon": 1, "evening": 2}
    ordered = sorted(actions, key=lambda a: (a.date, slot_order.get(a.time_slot, 0)))

    roots_by_sub: Dict[str, List[PlannedAction]] = {}
    last_comment_by_thread: Dict[str, PlannedAction] = {}

    for action in ordered:
        if action.post_type == "new_post":
            if not action.thread_id:
                action.thread_id = str(uuid.uuid4())
            roots_by_sub.setdefault(action.subreddit_name, []).append(action)
            continue

        roots = roots_by_sub.get(action.subreddit_name, [])
        if not roots:
            continue

        # Choose the most recent root authored by a different persona.
        root: Optional[PlannedAction] = None
        for candidate_root in reversed(roots):
            if candidate_root.persona_id != action.persona_id:
                root = candidate_root
                break
        if root is None or not root.thread_id:
            continue

        action.thread_id = root.thread_id

        if action.post_type == "top_comment":
            action.parent_action_id = root.id
            last_comment_by_thread[root.thread_id] = action
            continue

        # nested_reply: prefer replying to the latest comment in this thread.
        parent = last_comment_by_thread.get(root.thread_id)
        if parent is None:
            action.post_type = "top_comment"
            action.parent_action_id = root.id
            last_comment_by_thread[root.thread_id] = action
            continue

        # Avoid replying to yourself (same persona).
        if parent.persona_id == action.persona_id:
            action.post_type = "top_comment"
            action.parent_action_id = root.id
            last_comment_by_thread[root.thread_id] = action
            continue

        action.parent_action_id = parent.id
        last_comment_by_thread[root.thread_id] = action


def add_conversation_replies(
    actions: List[PlannedAction],
    week_index: int,
) -> List[PlannedAction]:
    """Optional: Add planned reply actions to create natural conversation threads.
    
    Call this AFTER generate_content_calendar if you want to schedule
    automatic follow-up replies to new posts from different personas.
    
    Note: This adds extra actions beyond the weekly target quota.
    """
    import random
    
    new_posts = [a for a in actions if a.post_type == "new_post" and a.thread_id]
    if not new_posts:
        return actions
    
    # Schedule replies for ~30% of new posts
    num_to_reply = max(1, len(new_posts) // 3)
    posts_to_reply = random.sample(new_posts, min(len(new_posts), num_to_reply))
    
    # Get unique personas from existing actions
    used_personas = list(set(a.persona_id for a in actions))
    
    for post in posts_to_reply:
        # Find a different persona for the reply (no ping-pong)
        other_personas = [p for p in used_personas if p != post.persona_id]
        if not other_personas:
            continue
        
        reply_persona = random.choice(other_personas)
        
        # Schedule reply for later in the day or next day
        post_date = datetime.strptime(post.date, "%Y-%m-%d")
        if post.time_slot == "morning":
            reply_slot: Literal["morning", "afternoon", "evening"] = "afternoon"
            reply_date = post_date
        elif post.time_slot == "afternoon":
            reply_slot = "evening"
            reply_date = post_date
        else:
            reply_slot = "morning"
            reply_date = post_date + timedelta(days=1)
        
        reply_action = PlannedAction(
            id=str(uuid.uuid4()),
            week_index=week_index,
            date=reply_date.strftime("%Y-%m-%d"),
            time_slot=reply_slot,
            subreddit_name=post.subreddit_name,
            persona_id=reply_persona,
            post_type="top_comment",
            content_idea_id=post.content_idea_id,
            prompt_brief="",
            quality_score=8.0,
            thread_id=post.thread_id,
            parent_action_id=post.id,
        )
        actions.append(reply_action)
    
    return actions


def _is_eligible(
    candidate: ContentIdea,
    target: WeeklyTarget,
    subreddit_counts: Dict[str, int],
    persona_counts: Dict[str, int],
    pillar_counts: Dict[str, int],
) -> bool:
    """Check if a candidate can be selected without violating hard quotas.
    
    Note: Pillar quotas are NOT hard caps - they are soft targets handled
    in scoring. This allows the planner to meet num_posts_per_week even
    when there are more pillars than posts.
    """
    # Check subreddit quota (hard cap)
    sub_quota = target.per_subreddit_quota.get(candidate.subreddit_name, 999)
    sub_used = subreddit_counts.get(candidate.subreddit_name, 0)
    if sub_used >= sub_quota:
        return False
    
    # Check persona quota (hard cap)
    persona_quota = target.per_persona_quota.get(candidate.persona_id, 999)
    persona_used = persona_counts.get(candidate.persona_id, 0)
    if persona_used >= persona_quota:
        return False
    
    # Pillar quotas are SOFT targets - not checked here
    # Overused pillars get penalized in scoring instead of being blocked
    # This ensures we can meet num_posts_per_week even with many pillars
    
    return True


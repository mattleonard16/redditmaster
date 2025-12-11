"""Weekly target builder for content distribution."""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import PostingHistoryEntry

from src.config.thresholds import POST_TYPE_RATIOS, PILLAR_ROTATION
from src.models import Persona, Subreddit, ContentPillar, WeeklyTarget


def build_weekly_target(
    num_posts_per_week: int,
    personas: List[Persona],
    subreddits: List[Subreddit],
    pillars: List[ContentPillar],
    history: Optional[List["PostingHistoryEntry"]] = None,
) -> WeeklyTarget:
    """Build target distribution for a week's content plan.
    
    This creates quotas and ratios that the selection algorithm will
    use to ensure balanced content distribution.
    
    Args:
        num_posts_per_week: Total number of actions to plan
        personas: Available personas
        subreddits: Target subreddits
        pillars: Content pillars to cover
        history: Optional posting history for pillar rotation
        
    Returns:
        A WeeklyTarget with quotas and ratios
    """
    # Build per-subreddit quotas from config
    per_subreddit_quota = {
        sub.name: min(sub.max_posts_per_week, num_posts_per_week)
        for sub in subreddits
    }
    
    # Build per-persona quotas from config
    per_persona_quota = {
        persona.id: min(persona.max_posts_per_week, num_posts_per_week)
        for persona in personas
    }
    
    # Build per-pillar quotas with rotation based on history
    per_pillar_quota = _compute_pillar_quotas(
        num_posts=num_posts_per_week,
        pillars=pillars,
        history=history,
    )
    
    return WeeklyTarget(
        total_actions=num_posts_per_week,
        new_post_share=POST_TYPE_RATIOS.get("new_post_share", 0.4),
        comment_share=POST_TYPE_RATIOS.get("comment_share", 0.6),
        per_subreddit_quota=per_subreddit_quota,
        per_persona_quota=per_persona_quota,
        per_pillar_quota=per_pillar_quota,
    )


def _compute_pillar_quotas(
    num_posts: int,
    pillars: List[ContentPillar],
    history: Optional[List["PostingHistoryEntry"]] = None,
) -> Dict[str, int]:
    """Compute pillar quotas with rotation based on history.
    
    Pillars that were heavily used recently get lower quotas,
    while underused pillars get higher quotas to ensure rotation.
    """
    if not pillars:
        return {}
    
    # Base quota per pillar
    base_quota = max(1, num_posts // len(pillars))
    
    if not history:
        # No history - equal distribution
        return {pillar.id: base_quota for pillar in pillars}
    
    # Count recent pillar usage (last 3 weeks / ~30 entries)
    lookback = PILLAR_ROTATION.get("history_lookback", 30)
    recent_entries = history[-lookback:]
    pillar_counts: Dict[str, int] = {}
    for entry in recent_entries:
        pillar_counts[entry.pillar_id] = pillar_counts.get(entry.pillar_id, 0) + 1
    
    # Calculate total and average
    total_recent = sum(pillar_counts.values())
    avg_per_pillar = total_recent / len(pillars) if total_recent > 0 else 0
    
    # Adjust quotas based on usage
    per_pillar_quota: Dict[str, int] = {}
    for pillar in pillars:
        count = pillar_counts.get(pillar.id, 0)
        
        if avg_per_pillar > 0:
            # Calculate usage ratio (1.0 = average, >1 = overused, <1 = underused)
            usage_ratio = count / avg_per_pillar if avg_per_pillar > 0 else 1.0
            
            # Adjust quota: boost underused, reduce overused
            overuse_threshold = PILLAR_ROTATION.get("overuse_threshold", 1.3)
            underuse_threshold = PILLAR_ROTATION.get("underuse_threshold", 0.7)
            
            if usage_ratio > overuse_threshold:
                # Overused - reduce quota
                adjusted_quota = max(1, int(base_quota * PILLAR_ROTATION.get("overuse_reduction", 0.5)))
            elif usage_ratio < underuse_threshold:
                # Underused - boost quota
                adjusted_quota = min(
                    num_posts,
                    int(base_quota * PILLAR_ROTATION.get("underuse_boost", 1.5)),
                )
            else:
                # Normal usage
                adjusted_quota = base_quota
        else:
            adjusted_quota = base_quota
        
        per_pillar_quota[pillar.id] = adjusted_quota
    
    return per_pillar_quota


def validate_target_feasibility(
    target: WeeklyTarget,
    personas: List[Persona],
    subreddits: List[Subreddit],
) -> List[str]:
    """Check if the target is feasible given constraints.
    
    Args:
        target: The weekly target to validate
        personas: Available personas
        subreddits: Target subreddits
        
    Returns:
        List of warning messages (empty if feasible)
    """
    warnings = []
    
    # Check if we have enough subreddit capacity
    total_subreddit_capacity = sum(target.per_subreddit_quota.values())
    if total_subreddit_capacity < target.total_actions:
        warnings.append(
            f"Total subreddit capacity ({total_subreddit_capacity}) is less than "
            f"target actions ({target.total_actions}). Some quotas may be exceeded."
        )
    
    # Check if we have enough persona capacity
    total_persona_capacity = sum(target.per_persona_quota.values())
    if total_persona_capacity < target.total_actions:
        warnings.append(
            f"Total persona capacity ({total_persona_capacity}) is less than "
            f"target actions ({target.total_actions}). Some quotas may be exceeded."
        )
    
    return warnings

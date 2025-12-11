"""Scoring algorithm for content ideas."""

from __future__ import annotations

from typing import Dict, List, Optional

from src.models import ContentIdea, WeeklyTarget, PostingHistoryEntry, ChatGPTQueryTemplate


def score_idea(
    idea: ContentIdea,
    weekly_target: WeeklyTarget,
    history: List[PostingHistoryEntry],
    current_subreddit_counts: Optional[Dict[str, int]] = None,
    current_persona_counts: Optional[Dict[str, int]] = None,
    current_pillar_counts: Optional[Dict[str, int]] = None,
    template: Optional[ChatGPTQueryTemplate] = None,
) -> float:
    """Score a content idea on a 0-10 scale.
    
    The score is composed of:
    - Relevance (0-4): How well the idea matches the target audience and funnel stage
    - Diversity (0-3): Penalizes repetition of pillar/subreddit/persona
    - Risk (0-3): Inverted risk score based on flags
    
    Args:
        idea: The content idea to score
        weekly_target: The target distribution
        history: Past posting history
        current_subreddit_counts: How many posts already assigned per subreddit
        current_persona_counts: How many posts already assigned per persona
        current_pillar_counts: How many posts already assigned per pillar
        template: Optional template for funnel stage scoring
        
    Returns:
        A score from 0-10 (higher is better)
    """
    current_subreddit_counts = current_subreddit_counts or {}
    current_persona_counts = current_persona_counts or {}
    current_pillar_counts = current_pillar_counts or {}
    
    relevance = _score_relevance(idea, weekly_target, current_pillar_counts, template)
    diversity = _score_diversity(
        idea, history, current_subreddit_counts, current_persona_counts
    )
    risk = _score_risk(idea, weekly_target, current_subreddit_counts)
    
    return relevance + diversity + risk


def _score_relevance(
    idea: ContentIdea, 
    target: WeeklyTarget,
    current_pillar_counts: Dict[str, int],
    template: Optional[ChatGPTQueryTemplate] = None,
) -> float:
    """Score relevance (0-4).
    
    Based on:
    - Match between subreddit and target audiences
    - Template stage vs post type alignment (awareness=questions, consideration=comparison, proof=stories)
    - Pillar quota progress (boost underused pillars, penalize overused)
    """
    score = 2.0  # Base score
    
    # Check pillar quota status (NOW ACTUALLY MEANINGFUL!)
    pillar_quota = target.per_pillar_quota.get(idea.pillar_id, 999)
    pillar_used = current_pillar_counts.get(idea.pillar_id, 0)
    
    if pillar_quota < 999:  # Has a real quota
        usage_ratio = pillar_used / pillar_quota if pillar_quota > 0 else 0
        
        if usage_ratio < 0.5:
            # Underused pillar - strong boost
            score += 1.5
        elif usage_ratio < 0.8:
            # Moderately used - mild boost
            score += 0.5
        elif usage_ratio >= 1.0:
            # Over quota - penalize to encourage diversity, but allow selection
            # (Pillar quotas are soft targets, not hard caps, per AGENTS.md)
            score -= 2.0
    
    # Prefer the right mix of post types
    if idea.post_type == "new_post":
        # New posts are valuable but shouldn't dominate
        score += 0.5
    elif idea.post_type == "top_comment":
        # Top comments are the bread and butter
        score += 1.0
    else:
        # Nested replies add authenticity
        score += 0.5
    
    # Consider template funnel stage (NEW!)
    if template:
        # Bonus for alignment between post type and funnel stage
        stage_bonus = _get_stage_alignment_bonus(idea.post_type, template.target_stage)
        score += stage_bonus
    
    return min(4.0, max(0.0, score))


def _get_stage_alignment_bonus(
    post_type: str,
    target_stage: str,
) -> float:
    """Calculate bonus for alignment between post type and funnel stage.
    
    Awareness (top of funnel): Questions and discussions work best
    Consideration (middle): Comparisons and how-tos work best  
    Proof (bottom): Case studies and experience shares work best
    """
    # These are soft preferences, not hard rules
    if target_stage == "awareness":
        # Awareness: new posts (questions) get bonus
        return 0.3 if post_type == "new_post" else 0.1
    elif target_stage == "consideration":
        # Consideration: comments (engaging discussions) get bonus
        return 0.3 if post_type == "top_comment" else 0.1
    elif target_stage == "proof":
        # Proof: any authentic contribution works
        return 0.2
    
    return 0.0


def _score_diversity(
    idea: ContentIdea,
    history: List[PostingHistoryEntry],
    subreddit_counts: Dict[str, int],
    persona_counts: Dict[str, int],
) -> float:
    """Score diversity (0-3).
    
    Penalizes if:
    - Same pillar + subreddit used recently
    - Same persona used repeatedly in that subreddit
    """
    score = 3.0  # Start with full score
    
    # Penalize if subreddit is heavily used
    sub_count = subreddit_counts.get(idea.subreddit_name, 0)
    if sub_count >= 3:
        score -= 1.5
    elif sub_count >= 2:
        score -= 0.75
    elif sub_count >= 1:
        score -= 0.25
    
    # Penalize if persona is heavily used
    persona_count = persona_counts.get(idea.persona_id, 0)
    if persona_count >= 4:
        score -= 1.0
    elif persona_count >= 2:
        score -= 0.5
    
    # Penalize if this pillar + subreddit combo was used recently
    recent_pillar_sub_combos = {
        (h.pillar_id, h.subreddit_name) for h in history[-20:]
    }
    if (idea.pillar_id, idea.subreddit_name) in recent_pillar_sub_combos:
        score -= 1.0

    # Penalize if (keyword_id, subreddit) was used recently (only when history includes keyword_ids)
    idea_keyword_ids = set(getattr(idea, "keyword_ids", []) or [])
    if idea_keyword_ids:
        recent_keyword_sub = set()
        for h in history[-30:]:
            h_kids = getattr(h, "keyword_ids", []) or []
            for kid in h_kids:
                recent_keyword_sub.add((kid, h.subreddit_name))
        if any((kid, idea.subreddit_name) in recent_keyword_sub for kid in idea_keyword_ids):
            score -= 0.75
    
    return max(0.0, score)


def _score_risk(
    idea: ContentIdea,
    target: WeeklyTarget,
    subreddit_counts: Dict[str, int],
) -> float:
    """Score risk (0-3, inverted from actual risk).
    
    Start with 3, subtract for:
    - Risk flags
    - Subreddits near their caps
    """
    score = 3.0
    
    # Penalize for risk flags
    flag_penalties = {
        "promotional": 1.5,
        "repetitive": 2.0,
        "similar_to_recent": 1.0,
        "spammy": 2.0,
        "off_topic": 1.5,
    }
    
    for flag in idea.risk_flags:
        score -= flag_penalties.get(flag, 0.5)
    
    # Penalize if subreddit is near quota
    sub_quota = target.per_subreddit_quota.get(idea.subreddit_name, 3)
    sub_used = subreddit_counts.get(idea.subreddit_name, 0)
    if sub_used >= sub_quota - 1:
        score -= 1.0
    elif sub_used >= sub_quota * 0.7:
        score -= 0.5
    
    return max(0.0, score)

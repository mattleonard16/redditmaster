"""Planning artifact data models for the Reddit Mastermind Planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class ContentPillar:
    """A content category/theme for organizing posts.
    
    Attributes:
        id: Unique identifier
        label: Human-readable label (e.g., "Problems", "Case studies")
    """
    id: str
    label: str


@dataclass
class ContentIdea:
    """A candidate content idea before selection.
    
    Attributes:
        id: Unique identifier
        company_id: Reference to the company
        pillar_id: Reference to the content pillar
        persona_id: Reference to the persona who would post this
        subreddit_name: Target subreddit
        template_id: Reference to the ChatGPT template used
        topic: Short human-readable topic label
        post_type: Type of Reddit action
        description: One-sentence description of the idea
        risk_flags: Potential issues (spammy, repetitive, etc.)
    """
    id: str
    company_id: str
    pillar_id: str
    persona_id: str
    subreddit_name: str
    template_id: str
    topic: str
    post_type: Literal["new_post", "top_comment", "nested_reply"]
    description: str = ""
    risk_flags: List[str] = field(default_factory=list)
    # Optional: keyword IDs (e.g., ["K1", "K14"]) for search/LLM query targeting
    keyword_ids: List[str] = field(default_factory=list)


@dataclass
class PlannedAction:
    """A scheduled action in the weekly calendar.
    
    Attributes:
        id: Unique identifier
        week_index: Which week this action belongs to
        date: ISO date string (YYYY-MM-DD)
        time_slot: Time of day for posting
        subreddit_name: Target subreddit
        persona_id: Who is posting
        post_type: Type of Reddit action
        content_idea_id: Reference to the content idea
        prompt_brief: Text to send to ChatGPT to draft the actual copy
        quality_score: Computed score 0-10
    """
    id: str
    week_index: int
    date: str
    time_slot: Literal["morning", "afternoon", "evening"]
    subreddit_name: str
    persona_id: str
    post_type: Literal["new_post", "top_comment", "nested_reply"]
    content_idea_id: str
    prompt_brief: str = ""
    quality_score: float = 0.0
    # Optional: denormalized metadata for downstream consumers (CSV export, history, UI)
    topic: str = ""
    pillar_id: str = ""
    keyword_ids: List[str] = field(default_factory=list)
    # Conversation threading fields
    thread_id: Optional[str] = None  # Groups related posts/comments together
    parent_action_id: Optional[str] = None  # For nested replies, points to parent


@dataclass
class WeeklyCalendar:
    """A week's worth of planned Reddit actions.
    
    Attributes:
        week_index: The week number (1-indexed)
        company_id: Reference to the company
        actions: List of planned actions for the week
    """
    week_index: int
    company_id: str
    actions: List[PlannedAction] = field(default_factory=list)


@dataclass
class WeeklyTarget:
    """Target distribution for a week's content plan.
    
    Attributes:
        total_actions: Total number of actions to plan
        new_post_share: Fraction of actions that should be new posts (0-1)
        comment_share: Fraction of actions that should be comments (0-1)
        per_subreddit_quota: Max actions per subreddit
        per_persona_quota: Max actions per persona
        per_pillar_quota: Min actions per pillar (to ensure coverage)
    """
    total_actions: int
    new_post_share: float = 0.4
    comment_share: float = 0.6
    per_subreddit_quota: Dict[str, int] = field(default_factory=dict)
    per_persona_quota: Dict[str, int] = field(default_factory=dict)
    per_pillar_quota: Dict[str, int] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """Quality evaluation of a weekly calendar.
    
    Attributes:
        overall_score: Aggregate score 0-10
        authenticity_score: How genuine the content sounds (0-10)
        diversity_score: Distribution across personas/subreddits/pillars (0-10)
        cadence_score: Posting frequency and timing (0-10)
        alignment_score: Coverage of value props and ICPs (0-10)
        warnings: Human-readable notes about issues
    """
    overall_score: float
    authenticity_score: float
    diversity_score: float
    cadence_score: float
    alignment_score: float
    warnings: List[str] = field(default_factory=list)

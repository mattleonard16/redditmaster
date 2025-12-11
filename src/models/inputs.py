"""Input data models for the Reddit Mastermind Planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Union


@dataclass
class CompanyInfo:
    """Company information used to generate content strategies.
    
    Attributes:
        id: Unique identifier for the company
        name: Company name
        description: Brief description of what the company does
        value_props: Core benefits/value propositions
        target_audiences: ICP (Ideal Customer Profile) descriptors
        tone: Content tone style
        banned_topics: Topics to avoid in all content
    """
    id: str
    name: str
    description: str
    value_props: List[str] = field(default_factory=list)
    target_audiences: List[str] = field(default_factory=list)
    tone: Union[Literal["casual", "technical", "formal", "playful"], str] = "casual"
    banned_topics: List[str] = field(default_factory=list)
    # Optional: keyword_id -> keyword/search query phrase (used primarily by CSV mode)
    keywords: Dict[str, str] = field(default_factory=dict)


@dataclass
class Persona:
    """A persona that will post or comment on Reddit.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name (e.g., "Bootstrapped founder")
        role: Role type (e.g., "founder", "customer", "lurker")
        stance: Relationship to the product
        expertise_level: How expert they sound
        max_posts_per_week: Posting quota to avoid spam detection
    """
    id: str
    name: str
    role: str
    stance: Literal["advocate", "skeptic", "neutral"] = "neutral"
    expertise_level: Literal["novice", "intermediate", "expert"] = "intermediate"
    max_posts_per_week: int = 5


@dataclass
class Subreddit:
    """A subreddit configuration for posting.
    
    Attributes:
        name: Subreddit name (e.g., "r/Entrepreneur")
        category: Category type (e.g., "startup", "design")
        max_posts_per_week: Weekly posting limit
        max_posts_per_day: Daily posting limit
    """
    name: str
    category: str
    max_posts_per_week: int = 3
    max_posts_per_day: int = 1


@dataclass
class ChatGPTQueryTemplate:
    """A prompt template for generating content ideas.
    
    Attributes:
        id: Unique identifier
        label: Human-readable label (e.g., "Founder pain question")
        template_string: The prompt pattern with placeholders
        target_stage: Funnel stage this template targets
        pillars: Optional list of content pillars this template applies to
    """
    id: str
    label: str
    template_string: str
    target_stage: Literal["awareness", "consideration", "proof"] = "awareness"
    pillars: List[str] = field(default_factory=list)

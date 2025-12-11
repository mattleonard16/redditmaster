"""History tracking for the Reddit Mastermind Planner."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class PostingHistoryEntry:
    """A record of a past post for de-duplication and rotation.
    
    Attributes:
        date: ISO date string (YYYY-MM-DD)
        subreddit_name: Where it was posted
        persona_id: Who posted it
        topic: The topic/angle used
        pillar_id: Which content pillar it belonged to
        week_index: Which week it was posted in
    """
    date: str
    subreddit_name: str
    persona_id: str
    topic: str
    pillar_id: str
    week_index: int = 1
    # Optional: keyword IDs associated with the topic (primarily for CSV/search targeting)
    keyword_ids: List[str] = field(default_factory=list)

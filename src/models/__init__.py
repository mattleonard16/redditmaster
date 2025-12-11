# Models package
"""Data structures for the Reddit Mastermind Planner."""

from .inputs import CompanyInfo, Persona, Subreddit, ChatGPTQueryTemplate
from .artifacts import (
    ContentPillar,
    ContentIdea,
    PlannedAction,
    WeeklyCalendar,
    WeeklyTarget,
    EvaluationReport,
)
from .history import PostingHistoryEntry

__all__ = [
    "CompanyInfo",
    "Persona",
    "Subreddit",
    "ChatGPTQueryTemplate",
    "ContentPillar",
    "ContentIdea",
    "PlannedAction",
    "WeeklyCalendar",
    "WeeklyTarget",
    "EvaluationReport",
    "PostingHistoryEntry",
]

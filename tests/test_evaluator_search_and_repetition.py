"""Tests for evaluator keyword coverage and cross-week repetition warnings."""

from src.evaluation.evaluator import evaluate_calendar
from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    WeeklyCalendar,
    PlannedAction,
    PostingHistoryEntry,
)


def test_keyword_coverage_warns_when_company_has_keywords_but_none_used():
    company = CompanyInfo(
        id="kco",
        name="KCo",
        description="Has keywords",
        keywords={"K1": "best ai presentation maker", "K2": "ai slide deck tool"},
    )

    personas = [Persona(id="p1", name="P1", role="user")]
    subreddits = [Subreddit(name="r/test", category="test")]

    cal = WeeklyCalendar(
        week_index=1,
        company_id=company.id,
        actions=[
            PlannedAction(
                id="a1",
                week_index=1,
                date="2025-01-01",
                time_slot="morning",
                subreddit_name="r/test",
                persona_id="p1",
                post_type="new_post",
                content_idea_id="i1",
                prompt_brief="some brief",
            )
        ],
    )

    evaluation = evaluate_calendar(cal, company, personas, subreddits)
    assert any("keyword" in w.lower() for w in evaluation.warnings)


def test_repetition_warns_on_repeated_topic_subreddit():
    company = CompanyInfo(id="rco", name="RCo", description="")
    personas = [Persona(id="p1", name="P1", role="user"), Persona(id="p2", name="P2", role="user")]
    subreddits = [Subreddit(name="r/test", category="test")]

    cal = WeeklyCalendar(
        week_index=2,
        company_id=company.id,
        actions=[
            PlannedAction(
                id="a1",
                week_index=2,
                date="2025-01-08",
                time_slot="morning",
                subreddit_name="r/test",
                persona_id="p2",
                post_type="new_post",
                content_idea_id="i1",
                prompt_brief="some brief",
                topic="Best AI Presentation Maker?",
                keyword_ids=["K1"],
            )
        ],
    )

    history = [
        PostingHistoryEntry(
            date="2025-01-01",
            subreddit_name="r/test",
            persona_id="p1",
            topic="Best AI Presentation Maker?",
            pillar_id="problems",
            week_index=1,
            keyword_ids=["K1"],
        )
    ]

    evaluation = evaluate_calendar(cal, company, personas, subreddits, history=history)
    assert any("repetition" in w.lower() for w in evaluation.warnings)

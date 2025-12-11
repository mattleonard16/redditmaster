"""Tests for conversation threading (parent_action_id / thread_id linking)."""

from collections import Counter

from src.models import CompanyInfo, Persona, Subreddit, ChatGPTQueryTemplate
from src.planning.calendar import generate_content_calendar


def test_calendar_links_some_threads_when_possible():
    company = CompanyInfo(
        id="threadco",
        name="ThreadCo",
        description="Test company for threaded conversations",
        value_props=["Speed"],
        target_audiences=["Builders"],
    )

    personas = [
        Persona(id="p1", name="P1", role="founder", max_posts_per_week=10),
        Persona(id="p2", name="P2", role="operator", max_posts_per_week=10),
        Persona(id="p3", name="P3", role="designer", max_posts_per_week=10),
    ]

    # Higher daily cap so multiple actions in same subreddit/week are possible.
    subreddits = [
        Subreddit(name="r/threadtest", category="test", max_posts_per_week=12, max_posts_per_day=3)
    ]

    templates = [
        ChatGPTQueryTemplate(
            id="t1",
            label="Questions",
            template_string="Ask about {topic}",
            target_stage="awareness",
        )
    ]

    calendar, _ = generate_content_calendar(
        company=company,
        personas=personas,
        subreddits=subreddits,
        templates=templates,
        num_posts_per_week=8,
        history=[],
        week_index=1,
        use_llm=False,
    )

    assert len(calendar.actions) >= 5

    # Expect at least one new post and at least one reply.
    type_counts = Counter(a.post_type for a in calendar.actions)
    assert type_counts.get("new_post", 0) >= 1
    assert any(a.parent_action_id for a in calendar.actions), "Expected some threaded replies"

    # No self-replies (same persona replying to itself)
    by_id = {a.id: a for a in calendar.actions}
    for a in calendar.actions:
        if not a.parent_action_id:
            continue
        parent = by_id.get(a.parent_action_id)
        if parent is None:
            continue
        assert parent.persona_id != a.persona_id

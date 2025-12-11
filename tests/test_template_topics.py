"""Tests for deterministic template-driven topic generation."""

from src.models import CompanyInfo, Subreddit, ChatGPTQueryTemplate, ContentPillar
from src.planning.ideas import _generate_topic


def test_contrarian_template_produces_opinion_even_if_awareness():
    company = CompanyInfo(
        id="c1",
        name="TestCo",
        description="desc",
        value_props=["automation"],
    )
    subreddit = Subreddit(name="r/test", category="startup")
    pillar = ContentPillar(id="opinions", label="Opinions / Contrarian Takes")
    template = ChatGPTQueryTemplate(
        id="hot_take",
        label="Hot take",
        template_string="Generate a thoughtful contrarian take on {topic}",
        target_stage="awareness",
        pillars=["opinions"],
    )

    topic = _generate_topic(company, pillar, template, subreddit)
    assert "opinion" in topic.lower() or "unpopular" in topic.lower()
    assert not topic.endswith("?"), "Contrarian templates should not default to questions"


def test_comparison_template_fills_unknown_placeholders():
    company = CompanyInfo(id="c1", name="TestCo", description="desc", value_props=["automation"])
    subreddit = Subreddit(name="r/test", category="startup")
    pillar = ContentPillar(id="comparisons", label="Comparisons / Teardowns")
    template = ChatGPTQueryTemplate(
        id="compare",
        label="Tool comparison",
        template_string="{toolA} vs {toolB} for {topic}",
        target_stage="consideration",
        pillars=["comparisons"],
    )

    topic = _generate_topic(company, pillar, template, subreddit)
    assert "{" not in topic and "}" not in topic
    assert "vs" in topic.lower()
    assert "automation" in topic.lower()


def test_stage_fallback_used_when_no_keywords():
    company = CompanyInfo(id="c1", name="TestCo", description="desc", value_props=["automation"])
    subreddit = Subreddit(name="r/test", category="startup")
    pillar = ContentPillar(id="case_studies", label="Case Studies / Success Stories")
    template = ChatGPTQueryTemplate(
        id="proof",
        label="Proof",
        template_string="Share something about {topic}",
        target_stage="proof",
        pillars=["case_studies"],
    )

    topic = _generate_topic(company, pillar, template, subreddit)
    assert "experience" in topic.lower() or "share" in topic.lower()

"""Tests for LLM prompt construction (no network)."""

from src.models import CompanyInfo, Persona, Subreddit, ContentPillar, ChatGPTQueryTemplate
from src.planning.llm import _build_idea_generation_prompt


def test_llm_prompt_includes_banned_topics():
    company = CompanyInfo(
        id="c1",
        name="TestCo",
        description="We make things better.",
        value_props=["Fast", "Easy"],
        target_audiences=["Founders"],
        banned_topics=["CompetitorX", "ForbiddenY"],
    )
    persona = Persona(id="p1", name="Tester", role="founder")
    subreddit = Subreddit(name="r/test", category="startup")
    pillar = ContentPillar(id="problems", label="Problems / Pains")
    template = ChatGPTQueryTemplate(
        id="test_template",
        label="Test question",
        template_string="Ask about {topic}",
        target_stage="awareness",
    )

    prompt = _build_idea_generation_prompt(
        company=company,
        persona=persona,
        subreddit=subreddit,
        pillar=pillar,
        template=template,
        num_ideas=2,
    )

    assert "Banned topics to avoid entirely" in prompt
    assert "CompetitorX" in prompt and "ForbiddenY" in prompt


def test_llm_prompt_has_authenticity_requirements():
    company = CompanyInfo(
        id="c1",
        name="TestCo",
        description="We make things better.",
    )
    persona = Persona(id="p1", name="Tester", role="founder")
    subreddit = Subreddit(name="r/test", category="startup")
    pillar = ContentPillar(id="opinions", label="Opinions / Contrarian Takes")
    template = ChatGPTQueryTemplate(
        id="test_template",
        label="Test opinion",
        template_string="Share opinion about {topic}",
        target_stage="awareness",
    )

    prompt = _build_idea_generation_prompt(
        company=company,
        persona=persona,
        subreddit=subreddit,
        pillar=pillar,
        template=template,
        num_ideas=1,
    )

    assert "Ideas should sound like a REAL Reddit user" in prompt
    assert "Avoid overt self-promotion" in prompt

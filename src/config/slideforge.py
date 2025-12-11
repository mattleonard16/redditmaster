"""SlideForge sample configuration for testing."""

from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
)


def get_slideforge_config() -> tuple[
    CompanyInfo,
    list[Persona],
    list[Subreddit],
    list[ChatGPTQueryTemplate],
]:
    """Get the SlideForge sample configuration.
    
    Returns:
        Tuple of (company, personas, subreddits, templates)
    """
    company = CompanyInfo(
        id="slideforge",
        name="SlideForge",
        description="AI-powered pitch deck creation tool that helps startups create investor-ready presentations in minutes instead of days",
        value_props=[
            "Create pitch decks 10x faster",
            "AI-generated content and design suggestions",
            "Templates based on successful funded startups",
            "Export to PowerPoint, Google Slides, or PDF",
        ],
        target_audiences=[
            "Early-stage startup founders",
            "Solo entrepreneurs",
            "Accelerator participants",
            "First-time fundraisers",
        ],
        tone="casual",
        banned_topics=[
            "competitor names",
            "pricing",
            "discounts",
            "guaranteed funding",
        ],
    )
    
    personas = [
        Persona(
            id="founder_advocate",
            name="Bootstrapped founder",
            role="founder",
            stance="advocate",
            expertise_level="intermediate",
            max_posts_per_week=4,
        ),
        Persona(
            id="designer_neutral",
            name="Freelance designer",
            role="designer",
            stance="neutral",
            expertise_level="expert",
            max_posts_per_week=3,
        ),
        Persona(
            id="curious_novice",
            name="First-time founder",
            role="aspiring_founder",
            stance="neutral",
            expertise_level="novice",
            max_posts_per_week=4,
        ),
    ]
    
    subreddits = [
        Subreddit(
            name="r/startups",
            category="startup",
            max_posts_per_week=3,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/Entrepreneur",
            category="business",
            max_posts_per_week=3,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/SaaS",
            category="saas",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/venturecapital",
            category="fundraising",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/design",
            category="design",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
    ]
    
    templates = [
        ChatGPTQueryTemplate(
            id="founder_pain",
            label="Founder pain question",
            template_string="Generate a question about a common founder pain point related to {topic}",
            target_stage="awareness",
            pillars=["problems"],
        ),
        ChatGPTQueryTemplate(
            id="howto_guide",
            label="How-to discussion",
            template_string="Generate a how-to discussion starter about {topic}",
            target_stage="consideration",
            pillars=["howto"],
        ),
        ChatGPTQueryTemplate(
            id="story_share",
            label="Experience share",
            template_string="Generate a story prompt about someone's experience with {topic}",
            target_stage="proof",
            pillars=["case_studies"],
        ),
        ChatGPTQueryTemplate(
            id="comparison_ask",
            label="Comparison question",
            template_string="Generate a question comparing different approaches to {topic}",
            target_stage="consideration",
            pillars=["comparisons"],
        ),
        ChatGPTQueryTemplate(
            id="hot_take",
            label="Opinion/hot take",
            template_string="Generate a thoughtful contrarian take on {topic}",
            target_stage="awareness",
            pillars=["opinions"],
        ),
        ChatGPTQueryTemplate(
            id="behind_scenes",
            label="Process discussion",
            template_string="Generate a behind-the-scenes discussion about {topic}",
            target_stage="proof",
            pillars=["behind_scenes"],
        ),
    ]
    
    return company, personas, subreddits, templates

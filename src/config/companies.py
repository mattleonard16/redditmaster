"""Additional company configurations for testing and demonstration."""

from __future__ import annotations

from typing import List, Tuple

from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
)


def get_devtools_config() -> Tuple[CompanyInfo, List[Persona], List[Subreddit], List[ChatGPTQueryTemplate]]:
    """Configuration for a developer tools company (B2B SaaS).
    
    Example: A CLI tool for code analysis.
    """
    company = CompanyInfo(
        id="codecheck",
        name="CodeCheck",
        description="AI-powered code review tool that catches bugs before they reach production",
        value_props=[
            "Catch bugs 10x faster than manual review",
            "Integrates with GitHub, GitLab, Bitbucket",
            "Learns your codebase patterns",
        ],
        target_audiences=[
            "Senior developers",
            "Engineering managers",
            "DevOps teams",
        ],
        tone="technical",
        banned_topics=["SonarQube", "CodeClimate", "competitor"],
    )
    
    personas = [
        Persona(
            id="senior_dev",
            name="Senior developer",
            role="developer",
            stance="neutral",
            expertise_level="expert",
            max_posts_per_week=4,
        ),
        Persona(
            id="eng_manager",
            name="Engineering manager",
            role="manager",
            stance="advocate",
            expertise_level="intermediate",
            max_posts_per_week=3,
        ),
        Persona(
            id="junior_curious",
            name="Curious junior dev",
            role="developer",
            stance="neutral",
            expertise_level="novice",
            max_posts_per_week=5,
        ),
    ]
    
    subreddits = [
        Subreddit(
            name="r/programming",
            category="programming",
            max_posts_per_week=3,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/webdev",
            category="web development",
            max_posts_per_week=3,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/devops",
            category="devops",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/ExperiencedDevs",
            category="senior developers",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
    ]
    
    templates = [
        ChatGPTQueryTemplate(
            id="pain_point",
            label="Developer pain",
            template_string="Discuss a common {topic} problem that developers face",
            target_stage="awareness",
            pillars=["problems"],
        ),
        ChatGPTQueryTemplate(
            id="best_practice",
            label="Best practice discussion",
            template_string="Share experiences with {topic}",
            target_stage="consideration",
            pillars=["howto", "case_studies"],
        ),
        ChatGPTQueryTemplate(
            id="tool_comparison",
            label="Tool comparison",
            template_string="Ask about different approaches to {topic}",
            target_stage="consideration",
            pillars=["comparisons"],
        ),
    ]
    
    return company, personas, subreddits, templates


def get_ecommerce_config() -> Tuple[CompanyInfo, List[Persona], List[Subreddit], List[ChatGPTQueryTemplate]]:
    """Configuration for an e-commerce/DTC brand.
    
    Example: A sustainable clothing brand.
    """
    company = CompanyInfo(
        id="ecothread",
        name="EcoThread",
        description="Sustainable fashion brand making clothes from recycled ocean plastic",
        value_props=[
            "Made from 100% recycled ocean plastic",
            "Carbon-neutral shipping",
            "Lifetime repair guarantee",
        ],
        target_audiences=[
            "Eco-conscious millennials",
            "Sustainable lifestyle advocates",
            "Fashion-forward consumers",
        ],
        tone="casual",
        banned_topics=["fast fashion", "Shein", "cheap alternatives"],
    )
    
    personas = [
        Persona(
            id="eco_advocate",
            name="Sustainability enthusiast",
            role="consumer",
            stance="advocate",
            expertise_level="intermediate",
            max_posts_per_week=4,
        ),
        Persona(
            id="fashion_curious",
            name="Fashion-curious buyer",
            role="consumer",
            stance="neutral",
            expertise_level="novice",
            max_posts_per_week=5,
        ),
        Persona(
            id="skeptic_convert",
            name="Converted skeptic",
            role="consumer",
            stance="neutral",
            expertise_level="intermediate",
            max_posts_per_week=3,
        ),
    ]
    
    subreddits = [
        Subreddit(
            name="r/sustainability",
            category="sustainability",
            max_posts_per_week=3,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/malefashionadvice",
            category="fashion",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/femalefashionadvice",
            category="fashion",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
        Subreddit(
            name="r/zerowaste",
            category="sustainability",
            max_posts_per_week=2,
            max_posts_per_day=1,
        ),
    ]
    
    templates = [
        ChatGPTQueryTemplate(
            id="lifestyle_q",
            label="Lifestyle question",
            template_string="Ask about sustainable {topic} choices",
            target_stage="awareness",
            pillars=["problems", "opinions"],
        ),
        ChatGPTQueryTemplate(
            id="product_experience",
            label="Product experience",
            template_string="Share experience with {topic}",
            target_stage="proof",
            pillars=["case_studies"],
        ),
    ]
    
    return company, personas, subreddits, templates


def get_minimal_config() -> Tuple[CompanyInfo, List[Persona], List[Subreddit], List[ChatGPTQueryTemplate]]:
    """Minimal configuration for edge case testing.
    
    Only 1 subreddit, 2 personas, low quotas.
    """
    company = CompanyInfo(
        id="minimal",
        name="MinimalCo",
        description="A minimal test company",
        value_props=["Simple", "Fast"],
        target_audiences=["Testers"],
        tone="casual",
        banned_topics=[],
    )
    
    personas = [
        Persona(
            id="persona_a",
            name="Persona A",
            role="user",
            stance="neutral",
            expertise_level="intermediate",
            max_posts_per_week=3,
        ),
        Persona(
            id="persona_b",
            name="Persona B",
            role="user",
            stance="advocate",
            expertise_level="novice",
            max_posts_per_week=3,
        ),
    ]
    
    subreddits = [
        Subreddit(
            name="r/test",
            category="testing",
            max_posts_per_week=5,
            max_posts_per_day=2,
        ),
    ]
    
    templates = [
        ChatGPTQueryTemplate(
            id="generic",
            label="Generic question",
            template_string="Discuss {topic}",
            target_stage="awareness",
            pillars=[],
        ),
    ]
    
    return company, personas, subreddits, templates


# Registry of all available configs
CONFIGS = {
    "slideforge": "get_slideforge_config",  # In slideforge.py
    "devtools": "get_devtools_config",
    "ecommerce": "get_ecommerce_config",
    "minimal": "get_minimal_config",
}


def get_config_by_name(name: str) -> Tuple[CompanyInfo, List[Persona], List[Subreddit], List[ChatGPTQueryTemplate]]:
    """Get a configuration by name.
    
    Args:
        name: One of 'slideforge', 'devtools', 'ecommerce', 'minimal'
        
    Returns:
        Tuple of (company, personas, subreddits, templates)
    """
    if name == "slideforge":
        from src.config.slideforge import get_slideforge_config
        return get_slideforge_config()
    elif name == "devtools":
        return get_devtools_config()
    elif name == "ecommerce":
        return get_ecommerce_config()
    elif name == "minimal":
        return get_minimal_config()
    else:
        raise ValueError(f"Unknown config: {name}. Available: {list(CONFIGS.keys())}")


def list_configs() -> List[str]:
    """List all available configuration names."""
    return list(CONFIGS.keys())

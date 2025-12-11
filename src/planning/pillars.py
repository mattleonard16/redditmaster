"""Content pillar derivation from company info."""

from __future__ import annotations

from typing import List, Optional

from src.models import CompanyInfo, ContentPillar


# Default pillars that apply to most companies
DEFAULT_PILLARS = [
    ContentPillar(id="problems", label="Problems / Pains"),
    ContentPillar(id="howto", label="How-to / Best Practices"),
    ContentPillar(id="case_studies", label="Case Studies / Success Stories"),
    ContentPillar(id="comparisons", label="Comparisons / Teardowns"),
    ContentPillar(id="opinions", label="Opinions / Contrarian Takes"),
    ContentPillar(id="behind_scenes", label="Behind the Scenes / Process"),
]


def derive_content_pillars(company: CompanyInfo) -> List[ContentPillar]:
    """Derive content pillars from company information.
    
    This uses a heuristic approach to generate 5-7 pillars based on
    the company's value props and target audiences. For now, we return
    the default pillars which work for most B2B companies.
    
    Args:
        company: The company information
        
    Returns:
        A list of 5-7 content pillars
        
    Future enhancement: Use LLM to generate custom pillars based on
    company description and value props.
    """
    # Start with default pillars
    pillars = list(DEFAULT_PILLARS)
    
    # If company has specific value props, we could customize pillars
    # For now, the defaults work well for most use cases
    
    # Optionally add a company-specific pillar based on primary offering
    if company.value_props:
        # Could derive a custom pillar here in the future
        pass
    
    return pillars


def get_pillar_by_id(pillars: List[ContentPillar], pillar_id: str) -> Optional[ContentPillar]:
    """Get a pillar by its ID.
    
    Args:
        pillars: List of content pillars
        pillar_id: The ID to look for
        
    Returns:
        The matching pillar or None
    """
    for pillar in pillars:
        if pillar.id == pillar_id:
            return pillar
    return None

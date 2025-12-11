"""OpenAI integration for content idea generation."""

from __future__ import annotations

import json
import os
from typing import List, Optional

# Load .env file for API keys (override=True to prefer .env over shell)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass  # dotenv not installed, rely on environment variables

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None  # type: ignore

from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ContentPillar,
    ContentIdea,
    ChatGPTQueryTemplate,
)


def get_openai_client() -> Optional["OpenAI"]:
    """Get an OpenAI client if available and configured.
    
    Returns:
        OpenAI client or None if not available
    """
    if not HAS_OPENAI:
        return None
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def generate_ideas_with_llm(
    company: CompanyInfo,
    persona: Persona,
    subreddit: Subreddit,
    pillar: ContentPillar,
    template: Optional["ChatGPTQueryTemplate"] = None,
    num_ideas: int = 3,
    client: Optional["OpenAI"] = None,
) -> List[dict]:
    """Generate content ideas using OpenAI.
    
    Args:
        company: Company information
        persona: The persona who would post
        subreddit: Target subreddit
        pillar: Content pillar to focus on
        template: Optional template to guide the angle and funnel stage
        num_ideas: Number of ideas to generate
        client: Optional OpenAI client (will create one if not provided)
        
    Returns:
        List of idea dictionaries with topic, post_type, description
    """
    if client is None:
        client = get_openai_client()
    
    if client is None:
        # Fall back to deterministic generation
        return []
    
    prompt = _build_idea_generation_prompt(
        company=company,
        persona=persona,
        subreddit=subreddit,
        pillar=pillar,
        template=template,
        num_ideas=num_ideas,
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Reddit content strategist. Generate realistic, "
                        "authentic Reddit post and comment ideas that sound like a "
                        "real community member, not a marketer. Output valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=1000,
        )
        
        content = response.choices[0].message.content
        if not content:
            return []
        
        # Parse JSON response
        ideas = _parse_llm_response(content)
        return ideas
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return []


def _build_idea_generation_prompt(
    company: CompanyInfo,
    persona: Persona,
    subreddit: Subreddit,
    pillar: ContentPillar,
    template: Optional["ChatGPTQueryTemplate"],
    num_ideas: int,
) -> str:
    """Build the prompt for idea generation."""
    value_props = ", ".join(company.value_props[:3]) if company.value_props else "general benefits"
    audiences = ", ".join(company.target_audiences[:2]) if company.target_audiences else "general audience"
    banned = ", ".join(company.banned_topics) if company.banned_topics else "None"
    
    # Add template guidance if available
    template_guidance = ""
    if template:
        stage_descriptions = {
            "awareness": "Focus on questions, problems, or general discussions that introduce topics (top of funnel)",
            "consideration": "Focus on comparisons, how-tos, or evaluating options (middle of funnel)",
            "proof": "Focus on case studies, success stories, or results (bottom of funnel)",
        }
        template_guidance = f"""
**Template Guidance** (shape ideas to match this angle):
- Template: {template.label}
- Pattern: {template.template_string}
- Funnel Stage: {template.target_stage} - {stage_descriptions.get(template.target_stage, '')}
"""
    
    return f"""Generate {num_ideas} realistic Reddit discussion ideas for the following:

**Company Context** (for your reference, not to mention directly):
- Name: {company.name}
- Description: {company.description}
- Key benefits: {value_props}
- Target audience: {audiences}
- Tone: {company.tone}
- Banned topics to avoid entirely: {banned}
{template_guidance}
**Persona** (who will be posting):
- Role: {persona.role} ({persona.name})
- Stance: {persona.stance}
- Expertise: {persona.expertise_level}

**Subreddit**: {subreddit.name} ({subreddit.category} community)

**Content Pillar**: {pillar.label}

**Requirements**:
- Ideas should sound like a REAL Reddit user, not a marketer
- No promotional language like "check out", "sign up", "book a demo"
- Avoid overt self-promotion like "we built/our product/my startup"
- Focus on genuine questions, experiences, or discussions relevant to the pillar
- Make the topic specific to the subreddit culture and audience
- Mix of post types: new_post, top_comment, nested_reply

Output as JSON array:
```json
[
  {{
    "topic": "Short topic label",
    "post_type": "new_post|top_comment|nested_reply",
    "description": "One-sentence description of the idea"
  }}
]
```

Generate {num_ideas} unique, high-quality ideas:"""


def _parse_llm_response(content: str) -> List[dict]:
    """Parse the LLM response into idea dictionaries."""
    # Try to extract JSON from the response
    try:
        # Handle markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()
        
        ideas = json.loads(content)
        
        # Validate structure
        valid_ideas = []
        for idea in ideas:
            if isinstance(idea, dict) and "topic" in idea and "post_type" in idea:
                # Normalize post_type
                post_type = idea.get("post_type", "top_comment")
                if post_type not in ["new_post", "top_comment", "nested_reply"]:
                    post_type = "top_comment"
                
                valid_ideas.append({
                    "topic": str(idea.get("topic", "")),
                    "post_type": post_type,
                    "description": str(idea.get("description", "")),
                })
        
        return valid_ideas
        
    except json.JSONDecodeError:
        return []


def is_llm_available() -> bool:
    """Check if LLM integration is available."""
    return HAS_OPENAI and os.environ.get("OPENAI_API_KEY") is not None

"""Prompt brief generation for ChatGPT."""

from __future__ import annotations

from typing import List

from src.models import (
    PlannedAction,
    ContentIdea,
    CompanyInfo,
    Persona,
    Subreddit,
)


def generate_prompt_brief(
    action: PlannedAction,
    idea: ContentIdea,
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
) -> str:
    """Generate a prompt brief for ChatGPT to draft the actual copy.
    
    The prompt brief provides:
    - Context about the persona and their voice
    - The topic and angle to cover
    - Guidelines for authenticity and avoiding spam
    
    Args:
        action: The planned action
        idea: The content idea behind the action
        company: Company information
        personas: All personas (to look up the one being used)
        subreddits: All subreddits (to look up context)
        
    Returns:
        A prompt string ready to send to ChatGPT
    """
    # Look up the persona
    persona = next((p for p in personas if p.id == idea.persona_id), None)
    persona_desc = _get_persona_description(persona) if persona else "a regular Reddit user"
    
    # Look up the subreddit
    subreddit = next((s for s in subreddits if s.name == idea.subreddit_name), None)
    subreddit_context = _get_subreddit_context(subreddit) if subreddit else ""

    business_goal = _get_business_goal_context()
    keyword_context = _get_keyword_context(company, idea)
    
    # Build the prompt based on post type
    if action.post_type == "new_post":
        prompt = _generate_new_post_prompt(
            idea=idea,
            company=company,
            persona_desc=persona_desc,
            subreddit_context=subreddit_context,
            business_goal=business_goal,
            keyword_context=keyword_context,
        )
    elif action.post_type == "top_comment":
        prompt = _generate_top_comment_prompt(
            idea=idea,
            company=company,
            persona_desc=persona_desc,
            subreddit_context=subreddit_context,
            business_goal=business_goal,
            keyword_context=keyword_context,
            is_reply=bool(action.parent_action_id),
        )
    else:  # nested_reply
        prompt = _generate_nested_reply_prompt(
            idea=idea,
            company=company,
            persona_desc=persona_desc,
            subreddit_context=subreddit_context,
            business_goal=business_goal,
            keyword_context=keyword_context,
        )
    
    return prompt


def _get_persona_description(persona: Persona) -> str:
    """Generate a description of how this persona should sound."""
    stance_desc = {
        "advocate": "who generally has positive experiences with solutions in this space",
        "skeptic": "who tends to be skeptical and asks tough questions",
        "neutral": "who is genuinely curious and open-minded",
    }
    
    expertise_desc = {
        "novice": "relatively new to this area, asks basic questions",
        "intermediate": "has some experience, can engage in nuanced discussions",
        "expert": "deeply knowledgeable, shares insights from experience",
    }
    
    return (
        f"a {persona.role} ({persona.name}) who is {expertise_desc.get(persona.expertise_level, '')} "
        f"and {stance_desc.get(persona.stance, '')}"
    )


def _get_subreddit_context(subreddit: Subreddit) -> str:
    """Generate context about the subreddit's culture."""
    return f"This is {subreddit.name}, a {subreddit.category} community."


def _generate_new_post_prompt(
    idea: ContentIdea,
    company: CompanyInfo,
    persona_desc: str,
    subreddit_context: str,
    business_goal: str,
    keyword_context: str,
) -> str:
    """Generate prompt for a new Reddit post."""
    company_context = _get_company_context(company)
    
    return f"""{business_goal}

Write a Reddit post for {idea.subreddit_name} from the perspective of {persona_desc}.

{subreddit_context}

Topic: {idea.topic}

{keyword_context}

{company_context}

Guidelines:
- Sound like a real person, not a marketer
- Ask genuine questions or share authentic experiences
- Do NOT mention the company by name unless it would be completely natural
- Avoid calls-to-action, sales language, or promotional phrases
- Keep it conversational and match the subreddit's tone
- Include a title and body text

The post should feel like it came from a real community member who happens to have relevant experience."""


def _generate_top_comment_prompt(
    idea: ContentIdea,
    company: CompanyInfo,
    persona_desc: str,
    subreddit_context: str,
    business_goal: str,
    keyword_context: str,
    is_reply: bool,
) -> str:
    """Generate prompt for a top-level comment."""
    company_context = _get_company_context(company)
    
    thread_hint = "You're replying inside a thread; keep continuity with prior comments." if is_reply else ""

    return f"""{business_goal}

Write a top-level Reddit comment in {idea.subreddit_name} responding to a discussion about: {idea.topic}

You are {persona_desc}.

{subreddit_context}

{keyword_context}

{thread_hint}

{company_context}

Guidelines:
- Respond as if you're replying to someone's question or discussion
- Add genuine value with your perspective or experience
- Only mention the company's benefits if it's directly relevant and natural
- Never sound like you're pushing a product
- Keep it helpful and community-oriented
- Match the casual tone of Reddit comments

The comment should feel like helpful advice from an experienced community member."""


def _generate_nested_reply_prompt(
    idea: ContentIdea,
    company: CompanyInfo,
    persona_desc: str,
    subreddit_context: str,
    business_goal: str,
    keyword_context: str,
) -> str:
    """Generate prompt for a nested reply."""
    company_context = _get_company_context(company)
    
    return f"""{business_goal}

Write a nested Reddit reply in {idea.subreddit_name} engaging in a thread about: {idea.topic}

You are {persona_desc}.

{subreddit_context}

{keyword_context}

{company_context}

Guidelines:
- You're replying to someone else's comment in a thread
- Build on what they said or respectfully offer a different perspective
- Keep it brief and conversational
- Only mention solutions if it flows naturally from the conversation
- Sound like you're having a real discussion, not selling

The reply should feel like natural engagement in an ongoing conversation."""


def _get_company_context(company: CompanyInfo) -> str:
    """Generate company context for the prompt."""
    value_props_str = ", ".join(company.value_props[:3]) if company.value_props else ""
    audiences_str = ", ".join(company.target_audiences[:2]) if company.target_audiences else ""
    
    context = f"Company context (for your background knowledge, not to mention explicitly): {company.name} - {company.description}"
    
    if value_props_str:
        context += f"\nKey benefits: {value_props_str}"
    
    if audiences_str:
        context += f"\nTarget audience: {audiences_str}"
    
    context += f"\nTone: {company.tone}"
    
    return context


def _get_business_goal_context() -> str:
    """Common business goal used in prompt briefs.

    Kept short to reduce token usage while still steering generation.
    """
    return (
        "BUSINESS GOAL (optimize for this):\n"
        "- Earn upvotes and genuine replies\n"
        "- Be useful enough that the thread could plausibly rank or be cited\n"
        "- Avoid anything that reads like an ad or coordinated shilling\n"
    )


def _get_keyword_context(company: CompanyInfo, idea: ContentIdea) -> str:
    """Add keyword/search-query targeting context when available."""
    keyword_ids = getattr(idea, "keyword_ids", []) or []
    if not keyword_ids:
        return ""

    phrases = []
    for kid in keyword_ids:
        phrase = (company.keywords or {}).get(kid)
        if phrase:
            phrases.append(f"{kid}: {phrase}")
        else:
            phrases.append(kid)

    return (
        "Target search/LLM queries (use naturally, no keyword stuffing):\n"
        f"- {', '.join(phrases)}"
    )

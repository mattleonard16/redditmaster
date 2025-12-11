"""Content idea generation from templates and company info."""

from __future__ import annotations

import re
import uuid
from typing import List, Literal, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.thresholds import SIMILARITY
from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
    ContentPillar,
    ContentIdea,
    PostingHistoryEntry,
)


_KEYWORD_ID_RE = re.compile(r"^k(\d+)$", re.IGNORECASE)


def _infer_keyword_ids(company: CompanyInfo, template: Optional[ChatGPTQueryTemplate]) -> List[str]:
    """Infer keyword IDs for an idea.

    In CSV mode we commonly create templates with ids like "k1", "k14".
    We normalize those to "K1", "K14" when they exist in company.keywords.
    """
    if not template:
        return []

    m = _KEYWORD_ID_RE.match(template.id)
    if not m:
        return []

    kid = f"K{m.group(1)}"
    if company.keywords and kid not in company.keywords:
        return []
    return [kid]


# Promotional phrases to flag (expanded for Day 2)
PROMOTIONAL_PHRASES = [
    "sign up",
    "book a demo",
    "check out",
    "try our",
    "use our",
    "visit our",
    "download",
    "subscribe",
    "buy now",
    "get started",
    "free trial",
    "limited time",
    "exclusive offer",
    "click here",
    "learn more at",
    "promo code",
    "discount",
    "special offer",
    "act now",
    "don't miss",
]

# Spammy patterns to detect
SPAMMY_PATTERNS = [
    "we built",
    "we created",
    "we launched",
    "i built",
    "i created",
    "i launched",
    "my startup",
    "my company",
    "our product",
    "our tool",
    "our platform",
    "our solution",
]


def generate_candidate_ideas(
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
    templates: List[ChatGPTQueryTemplate],
    pillars: List[ContentPillar],
    history: List[PostingHistoryEntry],
    use_llm: bool = True,
    debug_timing: bool = False,
) -> List[ContentIdea]:
    """Generate candidate content ideas for the week.
    
    Creates ideas by combining personas, subreddits, templates, and pillars.
    When LLM is available and use_llm=True, generates more creative ideas.
    Falls back to deterministic generation otherwise.
    
    Args:
        company: Company information
        personas: Available personas
        subreddits: Target subreddits
        templates: ChatGPT query templates
        pillars: Content pillars
        history: Past posting history for de-duplication
        use_llm: Whether to use LLM for idea generation (default True)
        debug_timing: If True, print timing information
        
    Returns:
        List of candidate ContentIdeas
    """
    import time
    ideas: List[ContentIdea] = []
    recent_topics = _get_recent_topics(history, lookback_weeks=3)
    
    # Try LLM generation if available
    llm_ideas = []
    if use_llm:
        if debug_timing:
            llm_start = time.time()
        
        llm_ideas = _generate_llm_ideas(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            pillars=pillars,
            recent_topics=recent_topics,
        )
        
        if debug_timing:
            print(f"[DEBUG]     LLM generation: {len(llm_ideas)} ideas in {time.time() - llm_start:.3f}s")
    
    # Add LLM-generated ideas
    ideas.extend(llm_ideas)
    
    # Always generate deterministic ideas as fallback/supplement
    if debug_timing:
        det_start = time.time()
    
    for pillar in pillars:
        # Get templates that match this pillar
        matching_templates = _get_templates_for_pillar(templates, pillar)
        if not matching_templates:
            # Use all templates if none specifically match
            matching_templates = templates[:2] if templates else []
        
        for subreddit in subreddits:
            for persona in personas:
                for template in matching_templates:
                    # Generate ideas for each post type
                    for post_type in ["new_post", "top_comment", "nested_reply"]:
                        idea = _create_idea(
                            company=company,
                            pillar=pillar,
                            subreddit=subreddit,
                            persona=persona,
                            template=template,
                            post_type=post_type,  # type: ignore
                            recent_topics=recent_topics,
                        )
                        if idea:
                            ideas.append(idea)
    
    if debug_timing:
        det_ideas = len(ideas) - len(llm_ideas)
        print(f"[DEBUG]     Deterministic generation: {det_ideas} ideas in {time.time() - det_start:.3f}s")
    
    return ideas


def _generate_llm_ideas(
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
    templates: List[ChatGPTQueryTemplate],
    pillars: List[ContentPillar],
    recent_topics: Set[str],
) -> List[ContentIdea]:
    """Generate ideas using LLM if available."""
    try:
        from src.planning.llm import generate_ideas_with_llm, is_llm_available
    except ImportError:
        return []
    
    if not is_llm_available():
        return []
    
    ideas: List[ContentIdea] = []

    # Build tasks for key combinations (limit API calls)
    tasks = []
    for pillar in pillars[:3]:  # Top 3 pillars
        matching_templates = _get_templates_for_pillar(templates, pillar)
        if not matching_templates:
            matching_templates = templates[:2] if templates else []
        template = matching_templates[0] if matching_templates else None

        for subreddit in subreddits[:3]:  # Top 3 subreddits
            for persona in personas[:2]:  # Top 2 personas
                tasks.append((pillar, subreddit, persona, template))

    if not tasks:
        return ideas

    # Bounded parallelism: keep quality coverage but reduce wall time.
    max_workers = min(4, len(tasks))

    def _call_llm(task):
        pillar, subreddit, persona, template = task
        results = generate_ideas_with_llm(
            company=company,
            persona=persona,
            subreddit=subreddit,
            pillar=pillar,
            template=template,
            num_ideas=2,
        )
        return task, results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_call_llm, t): t for t in tasks}
        for future in as_completed(futures):
            task, llm_results = future.result()
            pillar, subreddit, persona, template = task

            for result in llm_results:
                risk_flags = _compute_risk_flags(
                    topic=result.get("topic", ""),
                    description=result.get("description", ""),
                    subreddit_name=subreddit.name,
                    recent_topics=recent_topics,
                )

                ideas.append(
                    ContentIdea(
                        id=str(uuid.uuid4()),
                        company_id=company.id,
                        pillar_id=pillar.id,
                        persona_id=persona.id,
                        subreddit_name=subreddit.name,
                        template_id=template.id if template else "llm_generated",
                        topic=result.get("topic", ""),
                        post_type=result.get("post_type", "top_comment"),  # type: ignore
                        description=result.get("description", ""),
                        risk_flags=risk_flags,
                        keyword_ids=_infer_keyword_ids(company, template),
                    )
                )

    return ideas


def _create_idea(
    company: CompanyInfo,
    pillar: ContentPillar,
    subreddit: Subreddit,
    persona: Persona,
    template: ChatGPTQueryTemplate,
    post_type: Literal["new_post", "top_comment", "nested_reply"],
    recent_topics: Set[str],
) -> Optional[ContentIdea]:
    """Create a single content idea.
    
    Returns None if the idea should be filtered out (e.g., banned topic).
    """
    # Generate topic based on pillar and template
    topic = _generate_topic(company, pillar, template, subreddit)
    
    # Check banned topics
    for banned in company.banned_topics:
        if banned.lower() in topic.lower():
            return None
    
    # Generate description
    description = _generate_description(topic, persona, post_type)
    
    # Compute risk flags
    risk_flags = _compute_risk_flags(
        topic=topic,
        description=description,
        subreddit_name=subreddit.name,
        recent_topics=recent_topics,
    )
    
    return ContentIdea(
        id=str(uuid.uuid4()),
        company_id=company.id,
        pillar_id=pillar.id,
        persona_id=persona.id,
        subreddit_name=subreddit.name,
        template_id=template.id,
        topic=topic,
        post_type=post_type,
        description=description,
        risk_flags=risk_flags,
        keyword_ids=_infer_keyword_ids(company, template),
    )


def _generate_topic(
    company: CompanyInfo,
    pillar: ContentPillar,
    template: ChatGPTQueryTemplate,
    subreddit: Subreddit,
) -> str:
    """Generate a topic string for the idea.
    
    Uses the template pattern to shape the topic with company context.
    The template provides the angle/style, we generate a concrete topic.
    """
    # Prepare context for placeholders
    topic_context = company.value_props[0] if company.value_props else pillar.label
    category = subreddit.category

    template_raw = template.template_string or ""
    template_str = template_raw.lower()

    # Replace placeholders (avoid leaking raw {toolA} etc)
    placeholder_map = {
        "topic": topic_context,
        "category": category,
        "subreddit": subreddit.name,
        "company": company.name,
        "company_name": company.name,
        "toolA": "Tool A",
        "toolB": "Tool B",
        "tool_a": "Tool A",
        "tool_b": "Tool B",
    }

    def _fill_placeholders(s: str) -> str:
        def repl(match: re.Match) -> str:
            key = match.group(1)
            return (
                placeholder_map.get(key)
                or placeholder_map.get(key.lower())
                or topic_context
            )
        return re.sub(r"\{([^{}]+)\}", repl, s)

    filled = re.sub(r"\s+", " ", _fill_placeholders(template_raw)).strip()

    def _looks_instructional(s: str) -> bool:
        lower = s.lower()
        return any(
            w in lower
            for w in [
                "generate",
                "write",
                "create",
                "draft",
                "come up with",
                "discussion starter",
                "prompt",
            ]
        )

    # Determine explicit angle from template keywords FIRST.
    if any(k in template_str for k in ["contrarian", "hot take", "unpopular", "opinion"]):
        return f"Unpopular opinion about {topic_context} in {category}"

    if any(k in template_str for k in [" vs ", "versus", "compare", "compar"]):
        if filled and not _looks_instructional(filled):
            topic = filled
            if category.lower() not in topic.lower():
                topic = f"{topic} in {category}"
            return topic
        return f"Comparing approaches to {topic_context} in {category}"

    if any(k in template_str for k in ["behind-the-scenes", "behind the scenes", "behind", "process"]):
        return f"Behind the scenes: how we approach {topic_context} in {category}"

    if any(k in template_str for k in ["story", "experience", "case study", "success", "results"]):
        return f"My experience with {topic_context} in {category}"

    if any(k in template_str for k in ["how-to", "how to", "best practice", "best practices", "guide", "tutorial", "walkthrough"]):
        return f"How to handle {topic_context} in {category}"

    if any(k in template_str for k in ["question", "ask", "struggling", "pain", "problem", "issue"]):
        return f"How to handle {topic_context} in {category}?"

    # No explicit angle found: fall back to funnel stage.
    if template.target_stage == "awareness":
        return f"How to handle {topic_context} in {category}?"
    if template.target_stage == "consideration":
        if filled and not _looks_instructional(filled) and len(filled) <= 100:
            return filled
        return f"Best practices for {topic_context} in {category}"
    if template.target_stage == "proof":
        if filled and not _looks_instructional(filled) and len(filled) <= 100:
            return filled
        return f"My experience with {topic_context} in {category}"

    # Final fallback: cleaned template if it's user-facing, else generic.
    if filled and not _looks_instructional(filled) and len(filled) <= 100:
        return filled
    return f"{pillar.label}: {topic_context} in {category}"


def _generate_description(
    topic: str,
    persona: Persona,
    post_type: Literal["new_post", "top_comment", "nested_reply"],
) -> str:
    """Generate a description for the idea."""
    post_type_desc = {
        "new_post": "Start a new discussion thread",
        "top_comment": "Reply to an existing thread",
        "nested_reply": "Engage in a thread conversation",
    }
    
    return f"{persona.name} will {post_type_desc[post_type].lower()} about: {topic}"


def _get_templates_for_pillar(
    templates: List[ChatGPTQueryTemplate],
    pillar: ContentPillar,
) -> List[ChatGPTQueryTemplate]:
    """Get templates that match a specific pillar."""
    return [t for t in templates if pillar.id in t.pillars or pillar.label in t.pillars]


def _get_recent_topics(
    history: List[PostingHistoryEntry],
    lookback_weeks: int = 3,
) -> Set[str]:
    """Get topics used in recent weeks."""
    # For simplicity, just get all topics from history within lookback window
    # A more sophisticated version would compare week_index
    lookback = SIMILARITY.get("history_lookback_entries", 50)
    return {entry.topic.lower() for entry in history[-lookback:]}  # Last N entries


def _compute_risk_flags(
    topic: str,
    description: str = "",
    subreddit_name: str = "",
    recent_topics: Optional[Set[str]] = None,
) -> List[str]:
    """Compute risk flags for an idea.
    
    Enhanced for Day 2 with more comprehensive detection.
    """
    flags = []
    recent_topics = recent_topics or set()
    
    # Combine topic and description for analysis
    text_to_check = f"{topic} {description}".lower()
    
    # Check for promotional language
    for phrase in PROMOTIONAL_PHRASES:
        if phrase in text_to_check:
            flags.append("promotional")
            break
    
    # Check for spammy self-promotion patterns
    for pattern in SPAMMY_PATTERNS:
        if pattern in text_to_check:
            if "spammy" not in flags:
                flags.append("spammy")
            break
    
    # Check for topic repetition
    topic_lower = topic.lower()
    if topic_lower in recent_topics:
        flags.append("repetitive")
    
    # Check for similar topics
    similarity_threshold = SIMILARITY.get("topic_similarity_threshold", 0.7)
    for recent in recent_topics:
        if _topic_similarity(topic_lower, recent) > similarity_threshold:
            if "similar_to_recent" not in flags:
                flags.append("similar_to_recent")
            break
    
    # Check for excessive punctuation (spammy indicator)
    exclamation_count = text_to_check.count("!")
    question_count = text_to_check.count("?")
    if exclamation_count > 2 or (exclamation_count > 1 and question_count > 1):
        if "spammy" not in flags:
            flags.append("spammy")
    
    # Check for ALL CAPS words (spammy indicator)
    words = topic.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 2]
    if len(caps_words) >= 2:
        if "spammy" not in flags:
            flags.append("spammy")
    
    return flags


def _topic_similarity(topic1: str, topic2: str) -> float:
    """Simple similarity check between topics (0-1).
    
    For Day 1, this uses word overlap. Could use LLM embeddings later.
    """
    words1 = set(topic1.lower().split())
    words2 = set(topic2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0

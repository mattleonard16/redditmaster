"""CSV-based planner that orchestrates the full pipeline."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.csv.csv_parser import CompanyCSVData, PersonaInfo, parse_company_csv, extract_keywords_for_topic
from src.csv.csv_generator import (
    CalendarData,
    PlannedPost,
    PlannedComment,
    generate_calendar_csv,
    format_timestamp,
)
from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
    EvaluationReport,
    PostingHistoryEntry,
)
from src.planning.calendar import generate_content_calendar
from src.planning.llm import is_llm_available, get_openai_client


def generate_calendar_from_csv(
    company_csv: str,
    output_csv: str,
    week_index: int = 1,
    start_date: Optional[datetime] = None,
    use_llm: bool = True,
    history: Optional[List[PostingHistoryEntry]] = None,
) -> Tuple[CalendarData, EvaluationReport]:
    """Generate a content calendar from a company info CSV file.
    
    This is the main entry point for CSV-based calendar generation.
    
    Args:
        company_csv: Path to company info CSV file
        output_csv: Path, for output calendar CSV
        week_index: Week number (1-indexed)
        start_date: Start date for the week (defaults to next Monday)
        use_llm: Whether to use LLM for content generation
        
    Returns:
        Tuple of (CalendarData, EvaluationReport)
    """
    # Step 1: Parse company CSV
    csv_data = parse_company_csv(company_csv)
    
    # Step 2: Convert to internal models
    company, personas, subreddits, templates = _convert_to_internal_models(csv_data)
    
    # Step 3: Generate calendar using existing pipeline
    calendar, evaluation = generate_content_calendar(
        company=company,
        personas=personas,
        subreddits=subreddits,
        templates=templates,
        num_posts_per_week=csv_data.posts_per_week,
        history=history or [],
        week_index=week_index,
        start_date=start_date,
        use_llm=use_llm,
    )
    
    # Step 4: Convert to posts and comments with LLM-generated content
    calendar_data = _convert_to_csv_format(
        calendar=calendar,
        csv_data=csv_data,
        personas=personas,
        use_llm=use_llm,
        history=history or [],
    )
    
    # Step 5: Write CSV output
    generate_calendar_csv(calendar_data, output_csv)
    
    return calendar_data, evaluation


def _convert_to_internal_models(
    csv_data: CompanyCSVData,
) -> Tuple[CompanyInfo, List[Persona], List[Subreddit], List[ChatGPTQueryTemplate]]:
    """Convert CSV data to internal model objects."""
    
    # Company info
    company = CompanyInfo(
        id=csv_data.company_name.lower().replace(" ", "_") or "company",
        name=csv_data.company_name or "Company",
        description=csv_data.description,
        value_props=_extract_value_props(csv_data.description),
        target_audiences=_extract_audiences(csv_data.description),
        tone="casual",
        banned_topics=[],
        keywords=csv_data.keywords,
    )
    
    # Personas
    personas = [
        Persona(
            id=p.username,
            name=p.username.replace("_", " ").title(),
            role=p.role,
            stance=p.stance,
            expertise_level=p.expertise_level,
            max_posts_per_week=csv_data.posts_per_week,  # Each persona can handle all posts
        )
        for p in csv_data.personas
    ]
    
    # Ensure we have at least 2 personas
    if len(personas) < 2:
        personas.append(Persona(
            id="default_user",
            name="Default User",
            role="professional",
            stance="neutral",
            expertise_level="intermediate",
            max_posts_per_week=5,
        ))
    
    # Subreddits
    subreddits = [
        Subreddit(
            name=s if s.startswith("r/") else f"r/{s}",
            category=_infer_category(s),
            max_posts_per_week=2,
            max_posts_per_day=1,
        )
        for s in csv_data.subreddits[:10]  # Limit to 10 subreddits
    ]
    
    # Templates based on keywords
    templates = _generate_templates_from_keywords(csv_data.keywords)
    
    return company, personas, subreddits, templates


def _extract_value_props(description: str) -> List[str]:
    """Extract value propositions from description."""
    # Look for key benefit phrases
    props = []
    
    if "fast" in description.lower() or "quick" in description.lower():
        props.append("Fast and efficient")
    if "ai" in description.lower() or "automat" in description.lower():
        props.append("AI-powered automation")
    if "professional" in description.lower() or "polished" in description.lower():
        props.append("Professional quality output")
    if "easy" in description.lower() or "simple" in description.lower():
        props.append("Easy to use")
    
    return props or ["Saves time", "Improves quality"]


def _extract_audiences(description: str) -> List[str]:
    """Extract target audiences from description."""
    audiences = []
    desc_lower = description.lower()
    
    if "startup" in desc_lower or "founder" in desc_lower:
        audiences.append("Startup founders")
    if "consultant" in desc_lower:
        audiences.append("Consultants")
    if "sales" in desc_lower:
        audiences.append("Sales teams")
    if "student" in desc_lower or "educator" in desc_lower:
        audiences.append("Students and educators")
    
    return audiences or ["Professionals", "Teams"]


def _infer_category(subreddit: str) -> str:
    """Infer category from subreddit name."""
    sub_lower = subreddit.lower()
    
    if "startup" in sub_lower or "entrepreneur" in sub_lower:
        return "startup"
    elif "consult" in sub_lower:
        return "consulting"
    elif "sales" in sub_lower or "marketing" in sub_lower:
        return "business"
    elif "ai" in sub_lower or "chatgpt" in sub_lower or "claude" in sub_lower:
        return "ai"
    elif "design" in sub_lower or "canva" in sub_lower:
        return "design"
    elif "academ" in sub_lower or "teacher" in sub_lower or "education" in sub_lower:
        return "education"
    else:
        return "general"


def _generate_templates_from_keywords(keywords: Dict[str, str]) -> List[ChatGPTQueryTemplate]:
    """Generate query templates from keywords."""
    templates = []
    
    for kid, phrase in list(keywords.items())[:5]:
        templates.append(ChatGPTQueryTemplate(
            id=kid.lower(),
            label=phrase[:50],
            template_string=f"Discussion about {phrase}",
            target_stage="awareness",
            pillars=["problems"],
        ))
    
    # Add default templates
    templates.extend([
        ChatGPTQueryTemplate(
            id="pain_point",
            label="Pain point discussion",
            template_string="Struggling with {topic}",
            target_stage="awareness",
            pillars=["problems"],
        ),
        ChatGPTQueryTemplate(
            id="comparison",
            label="Tool comparison",
            template_string="{toolA} vs {toolB}",
            target_stage="consideration",
            pillars=["comparisons"],
        ),
    ])
    
    return templates


def _convert_to_csv_format(
    calendar,
    csv_data: CompanyCSVData,
    personas: List[Persona],
    use_llm: bool = True,
    history: Optional[List[PostingHistoryEntry]] = None,
) -> CalendarData:
    """Convert internal calendar to CSV format with generated content.
    
    In CSV mode, each action becomes a post, and comments are generated
    separately for each post (rather than using the internal post_type).
    """
    
    # In CSV mode, treat ALL actions as potential posts
    # Comments will be generated for each post separately
    # Use only the first N actions up to posts_per_week to match expected count
    post_actions = calendar.actions[:csv_data.posts_per_week]
    
    posts: List[PlannedPost] = []
    comments: List[PlannedComment] = []
    
    # Get persona list for rotation
    persona_list = [p.username for p in csv_data.personas] if csv_data.personas else [p.id for p in personas]
    
    history = history or []
    recent_topics = [h.topic for h in history[-20:] if h.topic]

    # Generate posts with persona rotation
    for i, action in enumerate(post_actions):
        post_id = f"P{i + 1}"
        
        # Rotate personas across posts for variety
        # Each post should have a different author when possible
        post_author = persona_list[i % len(persona_list)]
        
        # Generate title and body
        title, body = _generate_post_content(
            action=action,
            csv_data=csv_data,
            use_llm=use_llm,
            recent_topics=recent_topics,
        )
        
        # Extract matching keywords
        keyword_ids = extract_keywords_for_topic(title + " " + body, csv_data.keywords)
        
        posts.append(PlannedPost(
            post_id=post_id,
            subreddit=action.subreddit_name,
            title=title,
            body=body,
            author_username=post_author,  # Use rotated persona
            timestamp=format_timestamp(action.date, action.time_slot),
            keyword_ids=keyword_ids,
        ))
    
    # Generate comments for each post
    comment_idx = 1
    persona_list = [p.username for p in csv_data.personas] if csv_data.personas else [p.id for p in personas]
    
    for post in posts:
        # Generate 1-3 comments per post with variation
        num_comments = random.randint(1, 3)
        post_comments = _generate_comment_chain(
            post=post,
            num_comments=num_comments,
            personas=persona_list,
            csv_data=csv_data,
            start_comment_idx=comment_idx,
            use_llm=use_llm,
        )
        
        comments.extend(post_comments)
        comment_idx += len(post_comments)
    
    return CalendarData(posts=posts, comments=comments)


def _generate_post_content(
    action,
    csv_data: CompanyCSVData,
    use_llm: bool = True,
    recent_topics: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """Generate post title and body.
    
    Uses LLM if available, otherwise falls back to templates.
    """
    company_name = csv_data.company_name or "the tool"
    subreddit = action.subreddit_name
    
    if use_llm and is_llm_available():
        return _generate_post_with_llm(action, csv_data, recent_topics=recent_topics or [])
    
    # Template-based fallback - derive from keywords for any company
    # Get a sample keyword to make the post relevant
    sample_keyword = ""
    if csv_data.keywords:
        sample_keyword = list(csv_data.keywords.values())[0]
    
    # Extract a short topic from the keyword (avoid duplicate words like "best best")
    short_topic = sample_keyword.replace("best ", "").replace("top ", "").split()[0] if sample_keyword else "tool"
    sub_name = subreddit.replace("r/", "")
    
    # Generic templates that work for any company
    # Use subreddit context and keywords instead of hard-coded product references
    templates = [
        (
            f"Best {short_topic} tools for {sub_name}?",
            f"Looking for recommendations from this community. What's worked well for you? "
            f"Specifically interested in {sample_keyword or 'efficient workflows'}."
        ),
        (
            f"How do you handle {sample_keyword or 'this workflow'}?",
            f"Curious what approaches people here are using. "
            f"I've been researching options but would love real experiences."
        ),
        (
            f"Anyone tried tools for {sample_keyword or 'this use case'}?",
            f"Exploring different solutions and would appreciate any insights. "
            f"What's been your experience?"
        ),
    ]
    
    template = random.choice(templates)
    return template


def _generate_post_with_llm(
    action,
    csv_data: CompanyCSVData,
    recent_topics: List[str],
) -> Tuple[str, str]:
    """Generate post content using LLM with business-goal alignment."""
    client = get_openai_client()
    if not client:
        return _generate_post_content(action, csv_data, use_llm=False)
    
    # Find persona info
    persona_bio = ""
    persona_role = "professional"
    for p in csv_data.personas:
        if p.username == action.persona_id:
            persona_bio = p.bio[:500]
            persona_role = p.role
            break
    
    # Get relevant keywords for the prompt
    keywords_sample = list(csv_data.keywords.values())[:5]
    keywords_str = ", ".join(keywords_sample) if keywords_sample else "productivity tools"

    avoid_str = "\n".join(f"- {t[:80]}" for t in recent_topics[:8]) if recent_topics else "(none)"
    
    prompt = f"""You write Reddit posts for a B2B SaaS company.

BUSINESS GOAL:
- Earn upvotes, views, and genuine replies from the community
- Attract qualified inbound interest for the product
- Align posts with real search/ChatGPT queries so threads are useful enough to be cited or ranked

CONTEXT:
- Subreddit: {action.subreddit_name}
- Company area (do NOT mention by name): {csv_data.description[:200]}
- Persona: {action.persona_id} - {persona_role}
- Persona background: {persona_bio[:200] if persona_bio else 'A professional seeking advice'}
- Target keywords to naturally incorporate: {keywords_str}

GUIDELINES:
- Sound like a real {persona_role} in {action.subreddit_name}, not a marketer
- Frame a concrete problem, question, or story this persona would genuinely share
- Naturally incorporate target keyword phrases if possible, without stuffing
- Do NOT hard-sell or add obvious CTAs
- Title should be short, conversational, and invite discussion
- Body should be 1-3 sentences with specific context (not generic)
- Avoid repeating recent topics:
{avoid_str}

OPTIMIZE FOR:
- Usefulness and specificity (would people upvote or save this?)
- Authentic voice for the persona
- Likelihood that other Redditors would engage

Return JSON format only:
{{"title": "...", "body": "..."}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.85,
        )
        
        content = response.choices[0].message.content or ""
        
        # Parse JSON response
        import json
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        data = json.loads(content)
        return data.get("title", "Question for the community"), data.get("body", "Looking for advice.")
        
    except Exception as e:
        # Fallback to template
        return _generate_post_content(action, csv_data, use_llm=False)


def _generate_comment_chain(
    post: PlannedPost,
    num_comments: int,
    personas: List[str],
    csv_data: CompanyCSVData,
    start_comment_idx: int,
    use_llm: bool = True,
) -> List[PlannedComment]:
    """Generate a chain of comments for a post.
    
    Creates a natural conversation with replies.
    """
    comments = []
    
    # Filter out the post author from commenters
    other_personas = [p for p in personas if p != post.author_username]
    if not other_personas:
        other_personas = personas[:1]  # Use any persona if needed
    
    # Parse post timestamp to add comment times
    base_time = datetime.strptime(post.timestamp, "%Y-%m-%d %H:%M")
    
    parent_comment_id = None
    company_name = csv_data.company_name or "the tool"
    
    for i in range(num_comments):
        comment_id = f"C{start_comment_idx + i}"
        commenter = random.choice(other_personas)
        
        # Advance time for each comment
        comment_time = base_time + timedelta(minutes=15 + i * 12)
        
        # Generate comment text
        if use_llm and is_llm_available():
            comment_text = _generate_comment_with_llm(
                post, parent_comment_id, commenter, csv_data
            )
        else:
            comment_text = _generate_comment_template(
                post, parent_comment_id, company_name, i
            )
        
        comment = PlannedComment(
            comment_id=comment_id,
            post_id=post.post_id,
            parent_comment_id=parent_comment_id,
            comment_text=comment_text,
            username=commenter,
            timestamp=comment_time.strftime("%Y-%m-%d %H:%M"),
        )
        comments.append(comment)
        
        # Some comments are nested replies, some are top-level
        if i == 0 or random.random() > 0.6:
            parent_comment_id = comment_id  # Next will be a reply
        else:
            parent_comment_id = None  # Next will be top-level
    
    return comments


def _generate_comment_template(
    post: PlannedPost,
    parent_id: Optional[str],
    company_name: str,
    idx: int,
) -> str:
    """Generate comment using templates.
    
    Templates are designed to be helpful and neutral, not promotional.
    """
    
    if parent_id:
        # This is a reply - keep it conversational and neutral
        replies = [
            "Good suggestion, I'll look into that.",
            "Same experience here, thanks for sharing.",
            "That's helpful, appreciate the insight.",
            "Yeah that's been my experience too.",
            "Interesting, haven't tried that approach yet.",
        ]
        return random.choice(replies)
    else:
        # Top-level comment - share experience without hard-selling
        # Use company_name subtly as "one option" not "the best"
        top_comments = [
            f"I've tried a few tools for this. {company_name} was one that worked reasonably well for my use case, but YMMV depending on your needs.",
            f"Been using {company_name} lately. It's decent for the basics, though I still end up tweaking things manually.",
            f"I'd suggest trying a few options. {company_name} is one I've heard mentioned, along with some alternatives worth comparing.",
            f"From my experience, the key is finding something that fits your workflow. I've had okay results with {company_name} but there are other solid options too.",
        ]
        return random.choice(top_comments)


def _generate_comment_with_llm(
    post: PlannedPost,
    parent_id: Optional[str],
    commenter: str,
    csv_data: CompanyCSVData,
) -> str:
    """Generate comment using LLM with business-goal alignment."""
    client = get_openai_client()
    if not client:
        return _generate_comment_template(post, parent_id, csv_data.company_name or "the tool", 0)
    
    comment_type = "reply to a comment" if parent_id else "top-level comment"
    company_name = csv_data.company_name or "the tool"
    
    # Find commenter's persona info
    commenter_role = "professional"
    for p in csv_data.personas:
        if p.username == commenter:
            commenter_role = p.role
            break
    
    prompt = f"""You write Reddit comments for a B2B SaaS company.

BUSINESS GOAL:
- Earn upvotes and drive genuine engagement
- Move the conversation forward with useful information
- If mentioning {company_name}, do it as "this is what worked for me" rather than a pitch
- Align with search/ChatGPT queries so threads are useful enough to be cited

CONTEXT:
- Post title: {post.title}
- Post body: {post.body}
- Comment type: {comment_type}
- You are: {commenter} (a {commenter_role})

GUIDELINES:
- Write 1-2 sentences that sound natural and conversational
- Add details, examples, tradeoffs, or a short personal experience
- Avoid repeating the same talking points or phrases
- Do NOT be promotional or salesy
- Sound like a real Redditor, not a marketer

OPTIMIZE FOR:
- Usefulness (would people upvote this comment?)
- Authenticity (sounds like a real user sharing experience)
- Specificity (concrete details, not generic praise)

Return ONLY the comment text, nothing else.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.9,
        )
        
        return response.choices[0].message.content.strip() or "Good point!"
        
    except Exception:
        return _generate_comment_template(post, parent_id, company_name, 0)

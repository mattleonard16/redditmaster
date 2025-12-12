"""Calendar quality evaluation."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, TYPE_CHECKING

from src.config.thresholds import EVALUATION_THRESHOLDS, EVALUATION_WEIGHTS

from src.models import (
    WeeklyCalendar,
    CompanyInfo,
    Persona,
    Subreddit,
    EvaluationReport,
    PostingHistoryEntry,
)

if TYPE_CHECKING:
    from src.csv.csv_generator import CalendarData


def evaluate_calendar(
    calendar: WeeklyCalendar,
    company: CompanyInfo,
    personas: List[Persona],
    subreddits: List[Subreddit],
    history: Optional[List[PostingHistoryEntry]] = None,
) -> EvaluationReport:
    """Evaluate the quality of a weekly calendar.
    
    Scores the calendar on:
    - Authenticity: Do the prompts sound genuine?
    - Diversity: Good distribution across personas/subreddits/post types?
    - Cadence: No overposting, even distribution across days?
    - Alignment: Are we hitting key topics for the company?
    
    Args:
        calendar: The calendar to evaluate
        company: Company information
        personas: Available personas
        subreddits: Target subreddits
        
    Returns:
        An EvaluationReport with scores and warnings
    """
    warnings: List[str] = []
    
    authenticity = _evaluate_authenticity(calendar, warnings)
    diversity = _evaluate_diversity(calendar, personas, subreddits, warnings)
    cadence = _evaluate_cadence(calendar, subreddits, warnings)
    alignment = _evaluate_alignment(calendar, company, warnings)

    # Keyword/search-query targeting (bonus + warnings) when company provides keyword map.
    alignment = min(10.0, alignment + _evaluate_search_targeting(calendar, company, warnings))

    # Cross-week repetition checks (penalize only) when history is provided.
    if history:
        rep_penalty = _evaluate_repetition(calendar, history, warnings)
        authenticity = max(0.0, authenticity - rep_penalty)
    
    # Compute overall score as weighted average
    overall = (
        authenticity * EVALUATION_WEIGHTS.get("authenticity", 0.3) +
        diversity * EVALUATION_WEIGHTS.get("diversity", 0.25) +
        cadence * EVALUATION_WEIGHTS.get("cadence", 0.25) +
        alignment * EVALUATION_WEIGHTS.get("alignment", 0.2)
    )
    
    return EvaluationReport(
        overall_score=round(overall, 1),
        authenticity_score=round(authenticity, 1),
        diversity_score=round(diversity, 1),
        cadence_score=round(cadence, 1),
        alignment_score=round(alignment, 1),
        warnings=warnings,
    )


def _evaluate_authenticity(calendar: WeeklyCalendar, warnings: List[str]) -> float:
    """Evaluate how authentic the content sounds (0-10).
    
    Checks for:
    - Promotional language in prompt briefs
    - Balance of post types (too many new posts = suspicious)
    """
    if not calendar.actions:
        return 5.0
    
    score = 10.0
    
    # Check for promotional phrases in prompts
    promotional_phrases = [
        "sign up", "book a demo", "check out", "try our",
        "download", "subscribe", "buy now", "get started"
    ]
    
    promotional_count = 0
    for action in calendar.actions:
        brief_lower = action.prompt_brief.lower()
        for phrase in promotional_phrases:
            if phrase in brief_lower:
                promotional_count += 1
                break
    
    promotional_ratio = promotional_count / len(calendar.actions)
    warn_threshold = EVALUATION_THRESHOLDS.get("promotional_warning_threshold", 0.3)
    minor_threshold = EVALUATION_THRESHOLDS.get("promotional_minor_threshold", 0.1)
    if promotional_ratio > warn_threshold:
        score -= 3.0
        warnings.append(f"High promotional ratio: {promotional_ratio:.0%} of briefs contain promotional language")
    elif promotional_ratio > minor_threshold:
        score -= 1.5
    
    # Check post type distribution
    post_types = Counter(a.post_type for a in calendar.actions)
    new_post_ratio = post_types.get("new_post", 0) / len(calendar.actions)
    
    new_post_warning = EVALUATION_THRESHOLDS.get("new_post_warning_threshold", 0.6)
    new_post_minor = EVALUATION_THRESHOLDS.get("new_post_minor_threshold", 0.5)
    if new_post_ratio > new_post_warning:
        score -= 2.0
        warnings.append(f"Too many new posts ({new_post_ratio:.0%}), looks like spam")
    elif new_post_ratio > new_post_minor:
        score -= 1.0

    # Thread realism: some replies should exist for larger calendars
    threaded = [a for a in calendar.actions if getattr(a, "parent_action_id", None)]
    threaded_ratio = len(threaded) / len(calendar.actions)
    if len(calendar.actions) >= 6 and threaded_ratio < 0.15:
        score -= 1.5
        warnings.append("Low threading: few actions are replies (calendar may look manufactured)")
    elif len(calendar.actions) >= 6 and threaded_ratio < 0.25:
        score -= 0.5

    # Self-reply check: same persona replying to itself looks coordinated
    by_id = {a.id: a for a in calendar.actions}
    self_reply_count = 0
    for a in calendar.actions:
        parent_id = getattr(a, "parent_action_id", None)
        if not parent_id:
            continue
        parent = by_id.get(parent_id)
        if parent and parent.persona_id == a.persona_id:
            self_reply_count += 1
    if self_reply_count:
        score -= min(3.0, 1.0 + self_reply_count * 0.5)
        warnings.append(f"Found {self_reply_count} self-replies (same persona replying to itself)")
    
    return max(0.0, score)


def _evaluate_diversity(
    calendar: WeeklyCalendar,
    personas: List[Persona],
    subreddits: List[Subreddit],
    warnings: List[str],
) -> float:
    """Evaluate distribution across personas, subreddits, etc. (0-10)."""
    if not calendar.actions:
        return 5.0
    
    score = 10.0
    total = len(calendar.actions)
    
    # Check persona distribution
    persona_counts = Counter(a.persona_id for a in calendar.actions)
    persona_min = EVALUATION_THRESHOLDS.get("persona_min_count", 2)
    persona_dominance = EVALUATION_THRESHOLDS.get("persona_dominance_threshold", 0.6)
    if len(persona_counts) < min(persona_min, len(personas)):
        score -= 2.0
        warnings.append("Low persona diversity: using fewer than 2 personas")
    
    # Check for persona dominance
    max_persona_ratio = max(persona_counts.values()) / total
    if max_persona_ratio > persona_dominance:
        score -= 2.0
        warnings.append(f"Persona dominance: one persona has {max_persona_ratio:.0%} of posts")
    elif max_persona_ratio > 0.5:
        score -= 1.0
    
    # Check subreddit distribution
    subreddit_counts = Counter(a.subreddit_name for a in calendar.actions)
    subreddit_min = EVALUATION_THRESHOLDS.get("subreddit_min_count", 2)
    if len(subreddit_counts) < min(subreddit_min, len(subreddits)):
        score -= 2.0
        warnings.append("Low subreddit diversity: posting in fewer than 2 subreddits")
    
    # Check for subreddit dominance
    max_sub_ratio = max(subreddit_counts.values()) / total
    subreddit_dominance = EVALUATION_THRESHOLDS.get("subreddit_dominance_threshold", 0.5)
    if max_sub_ratio > subreddit_dominance:
        score -= 1.5
        warnings.append(f"Subreddit concentration: {max_sub_ratio:.0%} in one subreddit")
    elif max_sub_ratio > 0.4:
        score -= 0.75
    
    # Check post type distribution
    type_counts = Counter(a.post_type for a in calendar.actions)
    if len(type_counts) < 2:
        score -= 1.0
        warnings.append("Using only one post type")
    
    return max(0.0, score)


def _evaluate_cadence(
    calendar: WeeklyCalendar,
    subreddits: List[Subreddit],
    warnings: List[str],
) -> float:
    """Evaluate posting frequency and timing (0-10)."""
    if not calendar.actions:
        return 5.0
    
    score = 10.0
    
    # Build subreddit limits lookup
    subreddit_limits = {s.name: (s.max_posts_per_day, s.max_posts_per_week) for s in subreddits}
    
    # Check daily limits per subreddit
    daily_counts: Dict[str, Dict[str, int]] = {}  # date -> subreddit -> count
    for action in calendar.actions:
        if action.date not in daily_counts:
            daily_counts[action.date] = {}
        daily_counts[action.date][action.subreddit_name] = (
            daily_counts[action.date].get(action.subreddit_name, 0) + 1
        )
    
    for date, subs in daily_counts.items():
        for sub, count in subs.items():
            daily_limit, _ = subreddit_limits.get(sub, (2, 10))
            if count > daily_limit:
                score -= 2.0
                warnings.append(f"Overposting: {count} posts in {sub} on {date} (limit: {daily_limit})")
            elif count > 1:
                score -= 0.5
    
    # Check total per subreddit
    weekly_counts = Counter(a.subreddit_name for a in calendar.actions)
    for sub, count in weekly_counts.items():
        _, weekly_limit = subreddit_limits.get(sub, (2, 10))
        if count > weekly_limit:
            score -= 3.0
            warnings.append(f"Weekly limit exceeded: {count} posts in {sub} (limit: {weekly_limit})")
    
    # Check day distribution
    day_counts = Counter(a.date for a in calendar.actions)
    unique_days = len(day_counts)
    min_days_for_spread = EVALUATION_THRESHOLDS.get("min_days_for_spread_check", 4)
    if unique_days < min_days_for_spread and len(calendar.actions) >= 7:
        score -= 1.5
        warnings.append(f"Posts concentrated on too few days ({unique_days})")
    
    # Check time slot distribution
    slot_counts = Counter(a.time_slot for a in calendar.actions)
    min_slots = EVALUATION_THRESHOLDS.get("min_slots_for_variety", 2)
    if len(slot_counts) < min_slots and len(calendar.actions) >= 5:
        score -= 1.0
        warnings.append("Limited time slot variety")
    
    return max(0.0, score)


def _evaluate_alignment(
    calendar: WeeklyCalendar,
    company: CompanyInfo,
    warnings: List[str],
) -> float:
    """Evaluate coverage of company's value props and audiences (0-10)."""
    if not calendar.actions:
        return 5.0
    
    score = 8.0  # Start high, we can't perfectly measure this without topic analysis
    
    # Check that we have enough variety in topics
    # For now, this is a simple check based on action count
    min_actions_for_coverage = EVALUATION_THRESHOLDS.get("min_actions_for_coverage", 5)
    if len(calendar.actions) < min_actions_for_coverage:
        score -= 1.0
        warnings.append("Low action count limits value prop coverage")
    
    # Check prompt briefs mention different aspects
    # This is a rough heuristic - Day 2 will add better analysis
    if company.value_props:
        prop_mentions = 0
        for action in calendar.actions:
            brief_lower = action.prompt_brief.lower()
            for prop in company.value_props:
                if any(word in brief_lower for word in prop.lower().split()[:2]):
                    prop_mentions += 1
                    break
        
        coverage_ratio = prop_mentions / len(calendar.actions)
        coverage_threshold = EVALUATION_THRESHOLDS.get("value_prop_coverage_threshold", 0.3)
        if coverage_ratio < coverage_threshold:
            score -= 1.0
    
    return max(0.0, min(10.0, score))


def _evaluate_search_targeting(
    calendar: WeeklyCalendar,
    company: CompanyInfo,
    warnings: List[str],
) -> float:
    """Lightweight scoring for keyword/search-query coverage.

    Returns a small bonus (0-1.0) when keyword targeting is present and used.
    Adds warnings when keyword coverage is very low.
    """
    if not company.keywords:
        return 0.0

    used_keyword_ids = set()
    for a in calendar.actions:
        for kid in getattr(a, "keyword_ids", []) or []:
            used_keyword_ids.add(kid)

    if not used_keyword_ids:
        warnings.append("No keyword targets covered (company keywords present but none used)")
        return 0.0

    # Only require modest coverage: 1-2 keywords for small calendars, 3+ for larger.
    target = 1 if len(calendar.actions) <= 4 else 2 if len(calendar.actions) <= 8 else 3
    if len(used_keyword_ids) < target:
        warnings.append(
            f"Low keyword coverage: used {len(used_keyword_ids)} distinct keyword IDs (target: {target})"
        )
        return 0.2

    return 0.8


def _evaluate_repetition(
    calendar: WeeklyCalendar,
    history: List[PostingHistoryEntry],
    warnings: List[str],
) -> float:
    """Penalize repeating (topic, subreddit) or (keyword_id, subreddit) across weeks.

    Returns a penalty to subtract from authenticity.
    """
    if not history or not calendar.actions:
        return 0.0

    lookback_entries = history[-50:]
    recent_topic_sub = {
        ((h.topic or "").casefold().strip(), h.subreddit_name) for h in lookback_entries
    }

    recent_keyword_sub = set()
    for h in lookback_entries:
        for kid in getattr(h, "keyword_ids", []) or []:
            recent_keyword_sub.add((kid, h.subreddit_name))

    repeated_topic = 0
    repeated_keyword = 0
    for a in calendar.actions:
        topic = (getattr(a, "topic", "") or "").casefold().strip()
        if topic and (topic, a.subreddit_name) in recent_topic_sub:
            repeated_topic += 1
        for kid in getattr(a, "keyword_ids", []) or []:
            if (kid, a.subreddit_name) in recent_keyword_sub:
                repeated_keyword += 1

    penalty = 0.0
    if repeated_topic:
        penalty += min(2.0, repeated_topic * 0.5)
        warnings.append(f"Cross-week repetition: {repeated_topic} actions repeat a recent (topic, subreddit)")
    if repeated_keyword:
        penalty += min(1.5, repeated_keyword * 0.25)
        warnings.append(f"Cross-week repetition: {repeated_keyword} actions repeat a recent (keyword_id, subreddit)")

    return penalty


def evaluate_calendar_data(
    calendar_data: "CalendarData",
    company_name: str = "",
) -> EvaluationReport:
    """Evaluate the actual CalendarData output (after persona rotation).
    
    This evaluates the final output with correct persona attribution,
    unlike evaluate_calendar which checks the intermediate planning calendar.
    
    Args:
        calendar_data: The final CalendarData with posts and comments
        company_name: Company name for promotional language detection
        
    Returns:
        An EvaluationReport with accurate scores
    """
    warnings: List[str] = []
    
    posts = calendar_data.posts
    comments = calendar_data.comments
    
    if not posts:
        return EvaluationReport(
            overall_score=0.0,
            authenticity_score=0.0,
            diversity_score=0.0,
            cadence_score=0.0,
            alignment_score=0.0,
            warnings=["No posts generated"],
        )
    
    # === Authenticity (0-10) ===
    authenticity = 10.0
    
    # Check for promotional language in posts
    promo_phrases = ["check out", "you should try", "best tool", "must have", "game changer"]
    for post in posts:
        text = (post.title + " " + post.body).lower()
        if any(phrase in text for phrase in promo_phrases):
            authenticity -= 1.0
            warnings.append(f"Promotional language detected in post: {post.post_id}")
    
    # Penalize if company name is mentioned too prominently
    if company_name:
        mentions = sum(1 for p in posts if company_name.lower() in (p.title + p.body).lower())
        if mentions > len(posts) * 0.5:
            authenticity -= 2.0
            warnings.append("Company mentioned too frequently")
    
    authenticity = max(0.0, authenticity)
    
    # === Diversity (0-10) ===
    diversity = 10.0
    
    # Persona diversity
    unique_authors = set(p.author_username for p in posts)
    unique_commenters = set(c.username for c in comments)
    all_personas = unique_authors | unique_commenters
    
    if len(unique_authors) < 2 and len(posts) >= 2:
        diversity -= 2.0
        warnings.append("Low persona diversity: fewer than 2 post authors")
    
    # Subreddit diversity
    unique_subreddits = set(p.subreddit for p in posts)
    if len(unique_subreddits) < min(3, len(posts)):
        diversity -= 1.0
    
    # Check persona dominance
    author_counts = Counter(p.author_username for p in posts)
    if author_counts and len(posts) > 1:
        most_common = author_counts.most_common(1)[0]
        if most_common[1] / len(posts) > 0.6:
            diversity -= 1.5
            warnings.append(f"Persona dominance: {most_common[0]} has {most_common[1]}/{len(posts)} posts")
    
    diversity = max(0.0, diversity)
    
    # === Cadence (0-10) ===
    cadence = 10.0
    
    # Check for even distribution (basic check on timestamps)
    # For now, assume good cadence if posts exist
    if len(posts) < 3:
        cadence -= 1.0  # Small penalty for very few posts
    
    # === Alignment (0-10) ===
    alignment = 10.0
    
    # Check keyword usage
    posts_with_keywords = sum(1 for p in posts if p.keyword_ids)
    if posts_with_keywords < len(posts) * 0.5:
        alignment -= 1.0
        warnings.append("Low keyword usage in posts")
    
    # Compute overall score
    overall = (
        authenticity * EVALUATION_WEIGHTS.get("authenticity", 0.3) +
        diversity * EVALUATION_WEIGHTS.get("diversity", 0.25) +
        cadence * EVALUATION_WEIGHTS.get("cadence", 0.25) +
        alignment * EVALUATION_WEIGHTS.get("alignment", 0.2)
    )
    
    return EvaluationReport(
        overall_score=round(overall, 1),
        authenticity_score=round(authenticity, 1),
        diversity_score=round(diversity, 1),
        cadence_score=round(cadence, 1),
        alignment_score=round(alignment, 1),
        warnings=warnings,
    )

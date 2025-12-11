"""Configurable thresholds and constants for the Reddit Mastermind Planner.

This file centralizes all tunable parameters for easy adjustment.
Modify these values to tune the algorithm's behavior.
"""

# =============================================================================
# SCORING WEIGHTS
# =============================================================================

# How much each component contributes to the 0-10 score
SCORE_WEIGHTS = {
    "relevance_max": 4.0,      # Maximum points from relevance scoring
    "diversity_max": 3.0,      # Maximum points from diversity scoring
    "risk_max": 3.0,           # Maximum points from risk (inverted) scoring
}

# =============================================================================
# POST TYPE DISTRIBUTION
# =============================================================================

# Target ratio of new posts vs comments
POST_TYPE_RATIOS = {
    "new_post_share": 0.4,     # 40% new posts
    "comment_share": 0.6,      # 60% comments
}

# Bonus/penalty applied during selection to achieve target distribution
POST_TYPE_BONUSES = {
    "new_post_boost": 1.5,     # Score boost when we need more new posts
    "comment_boost": 0.5,      # Score boost when we have enough new posts
    "overuse_penalty": 1.0,    # Penalty when one type dominates (>60%)
}

# =============================================================================
# DIVERSITY PENALTIES
# =============================================================================

# Subreddit concentration penalties
SUBREDDIT_PENALTIES = {
    "heavy_use_threshold": 3,  # Posts in a subreddit before heavy penalty
    "medium_use_threshold": 2, # Posts before medium penalty
    "light_use_threshold": 1,  # Posts before light penalty
    "heavy_penalty": 1.5,
    "medium_penalty": 0.75,
    "light_penalty": 0.25,
}

# Persona concentration penalties
PERSONA_PENALTIES = {
    "heavy_use_threshold": 4,
    "medium_use_threshold": 2,
    "heavy_penalty": 1.0,
    "medium_penalty": 0.5,
}

# =============================================================================
# RISK FLAG PENALTIES
# =============================================================================

# Penalties applied when risk flags are detected
RISK_FLAG_PENALTIES = {
    "promotional": 1.5,
    "repetitive": 2.0,
    "similar_to_recent": 1.0,
    "spammy": 2.0,
    "off_topic": 1.5,
    "default": 0.5,           # For unknown flags
}

# =============================================================================
# PILLAR ROTATION
# =============================================================================

# How aggressively to rotate underused/overused pillars
PILLAR_ROTATION = {
    "overuse_threshold": 1.3,     # >130% of average = overused
    "underuse_threshold": 0.7,    # <70% of average = underused
    "overuse_reduction": 0.5,     # Reduce quota by 50%
    "underuse_boost": 1.5,        # Boost quota by 50%
    "history_lookback": 30,       # How many history entries to consider
}

# =============================================================================
# EVALUATION THRESHOLDS
# =============================================================================

# Weights for overall score calculation
EVALUATION_WEIGHTS = {
    "authenticity": 0.30,
    "diversity": 0.25,
    "cadence": 0.25,
    "alignment": 0.20,
}

# Thresholds for warnings
EVALUATION_THRESHOLDS = {
    # Authenticity
    "promotional_warning_threshold": 0.3,    # Warn if >30% promotional
    "promotional_minor_threshold": 0.1,      # Minor penalty if >10%
    "new_post_warning_threshold": 0.6,       # Warn if >60% new posts
    "new_post_minor_threshold": 0.5,         # Minor penalty if >50%
    
    # Diversity
    "persona_min_count": 2,                  # Warn if fewer personas used
    "persona_dominance_threshold": 0.6,      # Warn if one persona >60%
    "subreddit_min_count": 2,                # Warn if fewer subreddits
    "subreddit_dominance_threshold": 0.5,    # Warn if one sub >50%
    
    # Cadence
    "min_days_for_spread_check": 4,          # Min days for 7+ post calendars
    "min_slots_for_variety": 2,              # Min time slots for 5+ posts
    
    # Alignment
    "min_actions_for_coverage": 5,           # Min actions for value prop check
    "value_prop_coverage_threshold": 0.3,    # Warn if <30% mention props
}

# =============================================================================
# SIMILARITY DETECTION
# =============================================================================

SIMILARITY = {
    "topic_similarity_threshold": 0.7,       # Jaccard threshold for "similar"
    "history_lookback_entries": 50,          # Recent entries to check
}

# =============================================================================
# HARD LIMITS
# =============================================================================

HARD_LIMITS = {
    "max_score": 10.0,                       # Cap all scores at 10
    "min_score": 0.0,                        # Floor all scores at 0
    "max_daily_per_subreddit": 2,            # Default daily limit
    "max_weekly_per_subreddit": 5,           # Default weekly limit
    "max_weekly_per_persona": 7,             # Default persona limit
}

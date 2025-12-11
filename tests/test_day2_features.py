"""Tests for Day 2 features: LLM integration, risk flags, pillar rotation."""

import pytest
from collections import Counter

from src.config.slideforge import get_slideforge_config
from src.models import PostingHistoryEntry, ContentPillar
from src.planning.calendar import generate_content_calendar
from src.planning.targets import build_weekly_target
from src.planning.ideas import _compute_risk_flags, PROMOTIONAL_PHRASES, SPAMMY_PATTERNS


class TestRiskFlagDetection:
    """Tests for enhanced risk flag detection."""
    
    def test_promotional_phrases_detected(self):
        """Test that promotional phrases are flagged."""
        for phrase in PROMOTIONAL_PHRASES[:5]:  # Test a sample
            flags = _compute_risk_flags(
                topic=f"This is a topic with {phrase} in it",
                description="",
            )
            assert "promotional" in flags, f"Failed to detect promotional phrase: {phrase}"
    
    def test_spammy_patterns_detected(self):
        """Test that spammy self-promotion patterns are flagged."""
        for pattern in SPAMMY_PATTERNS[:5]:  # Test a sample
            flags = _compute_risk_flags(
                topic=f"Post about how {pattern} something",
                description="",
            )
            assert "spammy" in flags, f"Failed to detect spammy pattern: {pattern}"
    
    def test_excessive_punctuation_flagged(self):
        """Test that excessive punctuation is flagged as spammy."""
        flags = _compute_risk_flags(
            topic="WOW!!! This is AMAZING!!!",
            description="Check this out!!!",
        )
        assert "spammy" in flags
    
    def test_all_caps_flagged(self):
        """Test that ALL CAPS words are flagged."""
        flags = _compute_risk_flags(
            topic="THIS IS HUGE NEWS EVERYONE",
            description="",
        )
        assert "spammy" in flags
    
    def test_repetitive_topic_flagged(self):
        """Test that repetitive topics are flagged."""
        recent_topics = {"how to improve your workflow", "startup tips"}
        
        flags = _compute_risk_flags(
            topic="How to improve your workflow",
            recent_topics=recent_topics,
        )
        assert "repetitive" in flags
    
    def test_similar_topic_flagged(self):
        """Test that similar topics are flagged."""
        recent_topics = {"how to improve your workflow quickly"}
        
        flags = _compute_risk_flags(
            topic="How to improve your workflow easily",
            recent_topics=recent_topics,
        )
        assert "similar_to_recent" in flags
    
    def test_clean_topic_no_flags(self):
        """Test that a clean topic has no flags."""
        flags = _compute_risk_flags(
            topic="What are your thoughts on remote work?",
            description="Genuinely curious about experiences",
        )
        assert flags == []

    def test_promotional_and_spammy_combined(self):
        """Test that promotional and spammy flags both trigger on noisy pitches."""
        flags = _compute_risk_flags(
            topic="CHECK OUT our tool!!! Sign up today!!!",
            description="Limited time offer, don't miss out!!!",
        )
        assert "promotional" in flags
        assert "spammy" in flags


class TestPillarRotation:
    """Tests for pillar rotation based on history."""
    
    def test_no_history_equal_distribution(self):
        """Test that without history, pillars get equal quotas."""
        pillars = [
            ContentPillar(id="p1", label="Pillar 1"),
            ContentPillar(id="p2", label="Pillar 2"),
            ContentPillar(id="p3", label="Pillar 3"),
        ]
        
        company, personas, subreddits, templates = get_slideforge_config()
        
        target = build_weekly_target(
            num_posts_per_week=9,
            personas=personas,
            subreddits=subreddits,
            pillars=pillars,
            history=None,
        )
        
        # Each pillar should get ~3 quota
        assert target.per_pillar_quota["p1"] == 3
        assert target.per_pillar_quota["p2"] == 3
        assert target.per_pillar_quota["p3"] == 3
    
    def test_overused_pillar_reduced_quota(self):
        """Test that overused pillars get reduced quotas."""
        pillars = [
            ContentPillar(id="p1", label="Pillar 1"),
            ContentPillar(id="p2", label="Pillar 2"),
            ContentPillar(id="p3", label="Pillar 3"),
        ]
        
        # History heavily weighted towards p1
        history = [
            PostingHistoryEntry(
                date="2024-01-01",
                subreddit_name="r/test",
                persona_id="test",
                topic="Topic",
                pillar_id="p1",
                week_index=1,
            )
            for _ in range(20)  # p1 used 20 times
        ] + [
            PostingHistoryEntry(
                date="2024-01-02",
                subreddit_name="r/test",
                persona_id="test",
                topic="Topic",
                pillar_id="p2",
                week_index=1,
            )
            for _ in range(5)  # p2 used 5 times
        ]
        # p3 not used at all
        
        company, personas, subreddits, templates = get_slideforge_config()
        
        target = build_weekly_target(
            num_posts_per_week=9,
            personas=personas,
            subreddits=subreddits,
            pillars=pillars,
            history=history,
        )
        
        # p1 should have reduced quota (overused)
        # p3 should have boosted quota (underused)
        assert target.per_pillar_quota["p1"] <= target.per_pillar_quota["p3"]

    def test_underused_pillar_gets_boosted_quota(self):
        """Test that underused pillars are boosted relative to base quota."""
        pillars = [
            ContentPillar(id="p1", label="Pillar 1"),
            ContentPillar(id="p2", label="Pillar 2"),
            ContentPillar(id="p3", label="Pillar 3"),
        ]
        
        # History uses p1 heavily, p2 lightly, p3 never
        history = [
            PostingHistoryEntry(
                date="2024-01-01",
                subreddit_name="r/test",
                persona_id="test",
                topic="Topic",
                pillar_id="p1",
                week_index=1,
            )
            for _ in range(15)
        ] + [
            PostingHistoryEntry(
                date="2024-01-02",
                subreddit_name="r/test",
                persona_id="test",
                topic="Topic",
                pillar_id="p2",
                week_index=1,
            )
            for _ in range(3)
        ]
        # p3 unused
        
        company, personas, subreddits, templates = get_slideforge_config()
        
        target = build_weekly_target(
            num_posts_per_week=9,
            personas=personas,
            subreddits=subreddits,
            pillars=pillars,
            history=history,
        )
        
        base_quota = 9 // len(pillars)  # =3
        assert target.per_pillar_quota["p3"] > base_quota, "Underused pillar should be boosted"


class TestCLIIntegration:
    """Tests for CLI functionality."""
    
    def test_generate_with_history(self):
        """Test calendar generation with history."""
        company, personas, subreddits, templates = get_slideforge_config()
        
        # Create some history
        history = [
            PostingHistoryEntry(
                date="2024-01-01",
                subreddit_name="r/startups",
                persona_id="founder_advocate",
                topic="Week 1 topic",
                pillar_id="problems",
                week_index=1,
            )
            for _ in range(5)
        ]
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=history,
            week_index=2,
            use_llm=False,
        )
        
        # Should still generate a valid calendar
        assert len(calendar.actions) > 0
        assert evaluation.overall_score >= 5.0
    
    def test_no_llm_flag_works(self):
        """Test that disabling LLM still works."""
        company, personas, subreddits, templates = get_slideforge_config()
        
        # This should work without any LLM calls
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=5,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        assert len(calendar.actions) >= 3
        assert evaluation.overall_score >= 5.0

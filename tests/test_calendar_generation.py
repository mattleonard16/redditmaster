"""Tests for calendar generation end-to-end."""

import pytest
from datetime import datetime

from src.models import PostingHistoryEntry
from src.config.slideforge import get_slideforge_config
from src.planning.calendar import generate_content_calendar


class TestCalendarGeneration:
    """End-to-end tests for calendar generation."""
    
    @pytest.fixture
    def slideforge_config(self):
        """Get the SlideForge test configuration."""
        return get_slideforge_config()
    
    def test_basic_calendar_generation(self, slideforge_config):
        """Test that we can generate a basic calendar."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        assert calendar is not None
        assert calendar.week_index == 1
        assert calendar.company_id == "slideforge"
        assert len(calendar.actions) > 0
    
    def test_calendar_respects_num_posts(self, slideforge_config):
        """Test that calendar generates the requested number of posts."""
        company, personas, subreddits, templates = slideforge_config
        
        for num_posts in [5, 8, 10]:
            calendar, _ = generate_content_calendar(
                company=company,
                personas=personas,
                subreddits=subreddits,
                templates=templates,
                num_posts_per_week=num_posts,
                history=[],
                week_index=1,
                use_llm=False,
            )
            
            # Should be at or near the target (may be less if constraints limit)
            assert len(calendar.actions) <= num_posts
            assert len(calendar.actions) >= min(num_posts, 3)  # At least some actions
    
    def test_calendar_has_prompt_briefs(self, slideforge_config):
        """Test that all actions have prompt briefs."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        for action in calendar.actions:
            assert action.prompt_brief, f"Action {action.id} missing prompt brief"
            assert len(action.prompt_brief) > 50, "Prompt brief too short"
    
    def test_calendar_has_quality_scores(self, slideforge_config):
        """Test that all actions have quality scores."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        for action in calendar.actions:
            assert action.quality_score >= 0, "Quality score cannot be negative"
            assert action.quality_score <= 10, "Quality score cannot exceed 10"
    
    def test_evaluation_report(self, slideforge_config):
        """Test that evaluation report is generated."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        assert evaluation is not None
        assert 0 <= evaluation.overall_score <= 10
        assert 0 <= evaluation.authenticity_score <= 10
        assert 0 <= evaluation.diversity_score <= 10
        assert 0 <= evaluation.cadence_score <= 10
        assert 0 <= evaluation.alignment_score <= 10
    
    def test_good_evaluation_score(self, slideforge_config):
        """Test that a well-configured setup gets a good score."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        # With good config, we should get at least a fair score
        assert evaluation.overall_score >= 5.0, (
            f"Score too low: {evaluation.overall_score}, warnings: {evaluation.warnings}"
        )
    
    def test_calendar_dates_spread_across_week(self, slideforge_config):
        """Test that actions are spread across multiple days."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        dates = {action.date for action in calendar.actions}
        
        # Should use at least 3 different days for 10 posts
        assert len(dates) >= 3, f"Only {len(dates)} unique dates for 10 posts"
    
    def test_calendar_time_slots_varied(self, slideforge_config):
        """Test that actions use different time slots."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        slots = {action.time_slot for action in calendar.actions}
        
        # Should use at least 2 different time slots
        assert len(slots) >= 2, f"Only {len(slots)} unique time slots"
    
    def test_specific_start_date(self, slideforge_config):
        """Test that we can specify a start date."""
        company, personas, subreddits, templates = slideforge_config
        
        start = datetime(2024, 6, 10)  # A Monday
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,
            history=[],
            week_index=1,
            start_date=start,
            use_llm=False,
        )
        
        # All dates should be in the week starting June 10
        for action in calendar.actions:
            assert action.date.startswith("2024-06-1"), f"Date outside expected week: {action.date}"

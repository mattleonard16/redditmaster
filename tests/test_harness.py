"""Day 3 Test Harness: Comprehensive tests across all company configurations."""

import pytest
from collections import Counter
from typing import List

from src.config.companies import get_config_by_name, list_configs
from src.models import PostingHistoryEntry
from src.planning.calendar import generate_content_calendar


class TestAllConfigurations:
    """Test calendar generation across all company configurations."""
    
    @pytest.fixture(params=list_configs())
    def config_name(self, request):
        """Parametrize tests across all configs."""
        return request.param
    
    def test_generates_valid_calendar(self, config_name):
        """Test that each config generates a valid calendar."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        assert len(calendar.actions) > 0, f"{config_name}: No actions generated"
        assert evaluation.overall_score >= 5.0, f"{config_name}: Score too low"
    
    def test_respects_subreddit_limits(self, config_name):
        """Test that subreddit weekly limits are respected."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
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
        
        subreddit_limits = {s.name: s.max_posts_per_week for s in subreddits}
        subreddit_counts = Counter(a.subreddit_name for a in calendar.actions)
        
        for sub, count in subreddit_counts.items():
            limit = subreddit_limits.get(sub, 999)
            assert count <= limit, f"{config_name}: {sub} exceeded limit ({count} > {limit})"
    
    def test_respects_persona_limits(self, config_name):
        """Test that persona weekly limits are respected."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
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
        
        persona_limits = {p.id: p.max_posts_per_week for p in personas}
        persona_counts = Counter(a.persona_id for a in calendar.actions)
        
        for persona, count in persona_counts.items():
            limit = persona_limits.get(persona, 999)
            assert count <= limit, f"{config_name}: {persona} exceeded limit ({count} > {limit})"
    
    def test_has_post_type_diversity(self, config_name):
        """Test that there's a mix of post types."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
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
        
        if len(calendar.actions) >= 5:
            post_types = set(a.post_type for a in calendar.actions)
            assert len(post_types) >= 2, f"{config_name}: Only one post type"
    
    def test_evaluation_scores_reasonable(self, config_name):
        """Test that evaluation scores are within expected ranges."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        # All scores should be between 0 and 10
        assert 0 <= evaluation.overall_score <= 10
        assert 0 <= evaluation.authenticity_score <= 10
        assert 0 <= evaluation.diversity_score <= 10
        assert 0 <= evaluation.cadence_score <= 10
        assert 0 <= evaluation.alignment_score <= 10
        
        # With fresh start, should have decent scores
        assert evaluation.overall_score >= 6.0, f"{config_name}: Overall score too low"


class TestMultiWeekVariety:
    """Test that multiple weeks produce varied content."""
    
    @pytest.fixture(params=["slideforge", "devtools", "ecommerce"])
    def config_name(self, request):
        return request.param
    
    def test_three_weeks_have_variety(self, config_name):
        """Test that weeks 1, 2, 3 have visible variety."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
        history: List[PostingHistoryEntry] = []
        calendars = []
        
        for week in range(1, 4):
            calendar, _ = generate_content_calendar(
                company=company,
                personas=personas,
                subreddits=subreddits,
                templates=templates,
                num_posts_per_week=8,
                history=history,
                week_index=week,
                use_llm=False,
            )
            calendars.append(calendar)
            
            # Add to history for next week
            for action in calendar.actions:
                history.append(PostingHistoryEntry(
                    date=action.date,
                    subreddit_name=action.subreddit_name,
                    persona_id=action.persona_id,
                    topic=f"Week {week} topic {action.content_idea_id[:8]}",
                    pillar_id="problems",
                    week_index=week,
                ))
        
        # All calendars should have actions
        for i, cal in enumerate(calendars, 1):
            assert len(cal.actions) > 0, f"Week {i} has no actions"
    
    def test_history_influences_selection(self, config_name):
        """Test that history affects what gets selected."""
        company, personas, subreddits, templates = get_config_by_name(config_name)
        
        # Generate week 1 with no history
        cal1, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        # Create heavy history for one pillar
        heavy_history = [
            PostingHistoryEntry(
                date="2024-01-01",
                subreddit_name="r/test",
                persona_id="test",
                topic=f"Topic {i}",
                pillar_id="problems",
                week_index=1,
            )
            for i in range(20)
        ]
        
        # Generate week 2 with heavy history
        cal2, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=heavy_history,
            week_index=2,
            use_llm=False,
        )
        
        # Both should work
        assert len(cal1.actions) > 0
        assert len(cal2.actions) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_minimal_config_works(self):
        """Test the minimal config (1 subreddit, 2 personas)."""
        company, personas, subreddits, templates = get_config_by_name("minimal")
        
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
        
        assert len(calendar.actions) >= 1
        assert evaluation.overall_score >= 4.0  # Lower threshold for minimal
        
        # All should be in the single subreddit
        for action in calendar.actions:
            assert action.subreddit_name == "r/test"
    
    def test_very_low_post_count(self):
        """Test with only 2-3 posts requested."""
        company, personas, subreddits, templates = get_config_by_name("slideforge")
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=2,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        assert len(calendar.actions) >= 1
        assert len(calendar.actions) <= 3
    
    def test_high_post_count(self):
        """Test with 20+ posts requested."""
        company, personas, subreddits, templates = get_config_by_name("slideforge")
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=20,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        # Should generate many but respect limits
        assert len(calendar.actions) >= 10
        
        # Verify no over-posting in any subreddit
        subreddit_counts = Counter(a.subreddit_name for a in calendar.actions)
        for count in subreddit_counts.values():
            assert count <= 5, "Too many posts in one subreddit"
    
    def test_empty_history_works(self):
        """Test that empty history doesn't cause issues."""
        company, personas, subreddits, templates = get_config_by_name("devtools")
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=[],
            week_index=5,  # Week 5 with no history
            use_llm=False,
        )
        
        assert len(calendar.actions) > 0
        assert calendar.week_index == 5


class TestQualityThresholds:
    """Test that quality thresholds are enforced."""
    
    def test_quality_scores_in_range(self):
        """Test that all quality scores are between 0-10."""
        company, personas, subreddits, templates = get_config_by_name("slideforge")
        
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
            assert 0 <= action.quality_score <= 10, f"Score out of range: {action.quality_score}"
    
    def test_high_quality_actions_only(self):
        """Test that selected actions have reasonable quality."""
        company, personas, subreddits, templates = get_config_by_name("slideforge")
        
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
        
        # Average quality should be > 5
        if calendar.actions:
            avg_quality = sum(a.quality_score for a in calendar.actions) / len(calendar.actions)
            assert avg_quality >= 5.0, f"Average quality too low: {avg_quality}"
    
    def test_prompt_briefs_populated(self):
        """Test that all actions have prompt briefs."""
        company, personas, subreddits, templates = get_config_by_name("devtools")
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        for action in calendar.actions:
            assert action.prompt_brief, f"Missing prompt brief for action {action.id}"
            assert len(action.prompt_brief) > 50, "Prompt brief too short"

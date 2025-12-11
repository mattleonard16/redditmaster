"""Tests for multi-week calendar generation and variety."""

import pytest
from collections import Counter

from src.config.slideforge import get_slideforge_config
from src.models import PostingHistoryEntry
from src.planning.calendar import generate_content_calendar, calendar_to_history


class TestMultiWeekGeneration:
    """Tests for generating multiple weeks of content."""
    
    @pytest.fixture
    def slideforge_config(self):
        """Get the SlideForge test configuration."""
        return get_slideforge_config()
    
    def test_week_1_generation(self, slideforge_config):
        """Test that week 1 generates without history."""
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
        
        assert calendar.week_index == 1
        assert len(calendar.actions) > 0
        assert evaluation.overall_score >= 5.0
    
    def test_week_2_uses_history(self, slideforge_config):
        """Test that week 2 can use week 1 history."""
        company, personas, subreddits, templates = slideforge_config
        
        # Generate week 1
        calendar1, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        # Create history from week 1
        # Simple history entries (without full idea lookup)
        history = [
            PostingHistoryEntry(
                date=action.date,
                subreddit_name=action.subreddit_name,
                persona_id=action.persona_id,
                topic=f"Topic for {action.content_idea_id[:8]}",
                pillar_id="problems",  # Simplified
                week_index=1,
            )
            for action in calendar1.actions
        ]
        
        # Generate week 2 with history
        calendar2, evaluation2 = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=8,
            history=history,
            week_index=2,
            use_llm=False,
        )
        
        assert calendar2.week_index == 2
        assert len(calendar2.actions) > 0
        assert evaluation2.overall_score >= 5.0
    
    def test_three_weeks_variety(self, slideforge_config):
        """Test that weeks 1, 2, 3 have visible variety."""
        company, personas, subreddits, templates = slideforge_config
        
        history: list[PostingHistoryEntry] = []
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
        
        # Content idea IDs should be different across weeks
        all_idea_ids: list[str] = []
        for cal in calendars:
            all_idea_ids.extend([a.content_idea_id for a in cal.actions])
        
        # Should have mostly unique ideas (some overlap is ok due to regeneration)
        unique_ratio = len(set(all_idea_ids)) / len(all_idea_ids)
        assert unique_ratio >= 0.7, f"Too much idea repetition: {unique_ratio:.0%} unique"
    
    def test_week_index_embedded_in_actions(self, slideforge_config):
        """Test that actions have the correct week_index."""
        company, personas, subreddits, templates = slideforge_config
        
        for week in [1, 2, 5]:
            calendar, _ = generate_content_calendar(
                company=company,
                personas=personas,
                subreddits=subreddits,
                templates=templates,
                num_posts_per_week=5,
                history=[],
                week_index=week,
                use_llm=False,
            )
            
            for action in calendar.actions:
                assert action.week_index == week, (
                    f"Action has week_index {action.week_index}, expected {week}"
                )


class TestEdgeCases:
    """Tests for edge cases and unusual configurations."""
    
    def test_single_subreddit(self):
        """Test with only one subreddit."""
        from src.models import CompanyInfo, Persona, Subreddit, ChatGPTQueryTemplate
        
        company = CompanyInfo(
            id="single",
            name="Single Sub Co",
            description="A company that only posts in one place",
            value_props=["Fast"],
            target_audiences=["Everyone"],
        )
        
        personas = [
            Persona(id="p1", name="User", role="user", max_posts_per_week=5),
            Persona(id="p2", name="Customer", role="customer", max_posts_per_week=5),
        ]
        
        subreddits = [
            Subreddit(
                name="r/onlysub",
                category="niche",
                max_posts_per_week=10,
                max_posts_per_day=2,
            ),
        ]
        
        templates = [
            ChatGPTQueryTemplate(
                id="t1",
                label="Question",
                template_string="Ask about {topic}",
                target_stage="awareness",
            ),
        ]
        
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
        
        assert len(calendar.actions) > 0
        
        # All actions should be in the single subreddit
        for action in calendar.actions:
            assert action.subreddit_name == "r/onlysub"
    
    def test_two_personas_low_quota(self):
        """Test with minimal personas and low quotas."""
        from src.models import CompanyInfo, Persona, Subreddit, ChatGPTQueryTemplate
        
        company = CompanyInfo(
            id="minimal",
            name="Minimal Co",
            description="Minimal configuration test",
            value_props=["Simple"],
            target_audiences=["Testers"],
        )
        
        personas = [
            Persona(id="p1", name="User A", role="user", max_posts_per_week=2),
            Persona(id="p2", name="User B", role="user", max_posts_per_week=2),
        ]
        
        subreddits = [
            Subreddit(name="r/sub1", category="test", max_posts_per_week=3, max_posts_per_day=1),
            Subreddit(name="r/sub2", category="test", max_posts_per_week=3, max_posts_per_day=1),
        ]
        
        templates = [
            ChatGPTQueryTemplate(
                id="t1",
                label="Test",
                template_string="Test {topic}",
                target_stage="awareness",
            ),
        ]
        
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=3,  # Low target
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        assert len(calendar.actions) >= 1
        assert len(calendar.actions) <= 4  # Limited by persona quotas
        
        # Check persona limits
        persona_counts = Counter(a.persona_id for a in calendar.actions)
        for p, count in persona_counts.items():
            assert count <= 2, f"Persona {p} exceeded quota"

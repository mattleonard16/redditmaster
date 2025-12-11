"""Tests for quota and constraint enforcement."""

import pytest
from collections import Counter

from src.config.slideforge import get_slideforge_config
from src.models import CompanyInfo, Persona, Subreddit, ChatGPTQueryTemplate
from src.planning.calendar import generate_content_calendar


class TestQuotaEnforcement:
    """Tests for quota and limit enforcement."""
    
    @pytest.fixture
    def slideforge_config(self):
        """Get the SlideForge test configuration."""
        return get_slideforge_config()
    
    def test_subreddit_weekly_limit_respected(self, slideforge_config):
        """Test that subreddit weekly limits are not exceeded."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=15,  # Request more than limits allow
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        subreddit_limits = {s.name: s.max_posts_per_week for s in subreddits}
        subreddit_counts = Counter(a.subreddit_name for a in calendar.actions)
        
        for sub, count in subreddit_counts.items():
            limit = subreddit_limits.get(sub, 999)
            assert count <= limit, f"{sub} has {count} posts but limit is {limit}"
    
    def test_subreddit_daily_limit_respected(self, slideforge_config):
        """Test that subreddit daily limits are not exceeded."""
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
        
        subreddit_daily_limits = {s.name: s.max_posts_per_day for s in subreddits}
        
        # Count posts per day per subreddit
        daily_counts: dict[str, dict[str, int]] = {}
        for action in calendar.actions:
            if action.date not in daily_counts:
                daily_counts[action.date] = {}
            daily_counts[action.date][action.subreddit_name] = (
                daily_counts[action.date].get(action.subreddit_name, 0) + 1
            )
        
        for date, subs in daily_counts.items():
            for sub, count in subs.items():
                limit = subreddit_daily_limits.get(sub, 999)
                assert count <= limit, (
                    f"{sub} has {count} posts on {date} but daily limit is {limit}"
                )
    
    def test_persona_weekly_limit_respected(self, slideforge_config):
        """Test that persona weekly limits are not exceeded."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=15,  # Request more than limits allow
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        persona_limits = {p.id: p.max_posts_per_week for p in personas}
        persona_counts = Counter(a.persona_id for a in calendar.actions)
        
        for persona, count in persona_counts.items():
            limit = persona_limits.get(persona, 999)
            assert count <= limit, f"Persona {persona} has {count} posts but limit is {limit}"
    
    def test_no_duplicate_topic_subreddit_same_week(self, slideforge_config):
        """Test that the same topic isn't repeated in the same subreddit."""
        company, personas, subreddits, templates = slideforge_config
        
        # Generate with low count to see distinct topics
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
        
        # Check that each content_idea_id is unique
        idea_ids = [a.content_idea_id for a in calendar.actions]
        assert len(idea_ids) == len(set(idea_ids)), "Duplicate content ideas in calendar"
    
    def test_tight_constraints_dont_crash(self):
        """Test that very tight constraints produce a valid (possibly small) calendar."""
        company = CompanyInfo(
            id="tight",
            name="Tight Co",
            description="A test company with tight limits",
            value_props=["Speed"],
            target_audiences=["Developers"],
        )
        
        # Very restrictive personas
        personas = [
            Persona(id="p1", name="User 1", role="user", max_posts_per_week=2),
            Persona(id="p2", name="User 2", role="user", max_posts_per_week=2),
        ]
        
        # Very restrictive subreddits
        subreddits = [
            Subreddit(name="r/test1", category="test", max_posts_per_week=2, max_posts_per_day=1),
            Subreddit(name="r/test2", category="test", max_posts_per_week=2, max_posts_per_day=1),
        ]
        
        templates = [
            ChatGPTQueryTemplate(
                id="t1",
                label="Test",
                template_string="Test {topic}",
                target_stage="awareness",
            ),
        ]
        
        # Request more than constraints allow
        calendar, evaluation = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=10,  # Can't actually do 10
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        # Should still produce a valid calendar
        assert calendar is not None
        assert evaluation is not None
        
        # Check limits are respected
        persona_counts = Counter(a.persona_id for a in calendar.actions)
        for p, count in persona_counts.items():
            assert count <= 2, f"Persona {p} exceeded limit"
        
        subreddit_counts = Counter(a.subreddit_name for a in calendar.actions)
        for s, count in subreddit_counts.items():
            assert count <= 2, f"Subreddit {s} exceeded limit"


class TestPillarDistribution:
    """Tests for pillar distribution (avoid >40% in one pillar)."""
    
    @pytest.fixture
    def slideforge_config(self):
        """Get the SlideForge test configuration."""
        return get_slideforge_config()
    
    def test_pillar_distribution_not_degenerate(self, slideforge_config):
        """Test that pillars are somewhat evenly distributed."""
        company, personas, subreddits, templates = slideforge_config
        
        calendar, _ = generate_content_calendar(
            company=company,
            personas=personas,
            subreddits=subreddits,
            templates=templates,
            num_posts_per_week=12,
            history=[],
            week_index=1,
            use_llm=False,
        )
        
        if len(calendar.actions) < 3:
            pytest.skip("Too few actions to test distribution")
        
        # Note: We don't have direct pillar info in actions, 
        # but the evaluation should flag this
        # For now, just verify we have diversity in post types
        post_types = Counter(a.post_type for a in calendar.actions)
        
        # Should have at least 2 different post types for 12 posts
        assert len(post_types) >= 2, "All posts are the same type"

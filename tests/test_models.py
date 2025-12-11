"""Tests for data models."""

import pytest
from src.models import (
    CompanyInfo,
    Persona,
    Subreddit,
    ChatGPTQueryTemplate,
    ContentPillar,
    ContentIdea,
    PlannedAction,
    WeeklyCalendar,
    WeeklyTarget,
    EvaluationReport,
    PostingHistoryEntry,
)


class TestInputModels:
    """Tests for input data models."""
    
    def test_company_info_creation(self):
        """Test creating a CompanyInfo object."""
        company = CompanyInfo(
            id="test",
            name="Test Company",
            description="A test company",
            value_props=["Fast", "Easy", "Cheap"],
            target_audiences=["Developers", "Startups"],
            tone="casual",
            banned_topics=["competitor"],
        )
        
        assert company.id == "test"
        assert company.name == "Test Company"
        assert len(company.value_props) == 3
        assert "Developers" in company.target_audiences
    
    def test_company_info_defaults(self):
        """Test CompanyInfo default values."""
        company = CompanyInfo(
            id="test",
            name="Test",
            description="Test",
        )
        
        assert company.tone == "casual"
        assert company.value_props == []
        assert company.banned_topics == []
    
    def test_persona_creation(self):
        """Test creating a Persona object."""
        persona = Persona(
            id="p1",
            name="Tech Founder",
            role="founder",
            stance="advocate",
            expertise_level="expert",
            max_posts_per_week=5,
        )
        
        assert persona.id == "p1"
        assert persona.stance == "advocate"
        assert persona.expertise_level == "expert"
    
    def test_persona_defaults(self):
        """Test Persona default values."""
        persona = Persona(
            id="p1",
            name="User",
            role="user",
        )
        
        assert persona.stance == "neutral"
        assert persona.expertise_level == "intermediate"
        assert persona.max_posts_per_week == 5
    
    def test_subreddit_creation(self):
        """Test creating a Subreddit object."""
        sub = Subreddit(
            name="r/test",
            category="general",
            max_posts_per_week=5,
            max_posts_per_day=2,
        )
        
        assert sub.name == "r/test"
        assert sub.max_posts_per_week == 5
    
    def test_template_creation(self):
        """Test creating a ChatGPTQueryTemplate object."""
        template = ChatGPTQueryTemplate(
            id="t1",
            label="Test template",
            template_string="Generate content about {topic}",
            target_stage="awareness",
            pillars=["problems", "howto"],
        )
        
        assert template.id == "t1"
        assert "problems" in template.pillars


class TestArtifactModels:
    """Tests for artifact data models."""
    
    def test_content_pillar_creation(self):
        """Test creating a ContentPillar object."""
        pillar = ContentPillar(id="problems", label="Problems / Pains")
        
        assert pillar.id == "problems"
        assert "Problems" in pillar.label
    
    def test_content_idea_creation(self):
        """Test creating a ContentIdea object."""
        idea = ContentIdea(
            id="i1",
            company_id="c1",
            pillar_id="problems",
            persona_id="p1",
            subreddit_name="r/test",
            template_id="t1",
            topic="Test topic",
            post_type="new_post",
            description="A test idea",
            risk_flags=["promotional"],
        )
        
        assert idea.id == "i1"
        assert idea.post_type == "new_post"
        assert "promotional" in idea.risk_flags
    
    def test_planned_action_creation(self):
        """Test creating a PlannedAction object."""
        action = PlannedAction(
            id="a1",
            week_index=1,
            date="2024-01-15",
            time_slot="morning",
            subreddit_name="r/test",
            persona_id="p1",
            post_type="top_comment",
            content_idea_id="i1",
            prompt_brief="Write a comment...",
            quality_score=8.5,
        )
        
        assert action.week_index == 1
        assert action.time_slot == "morning"
        assert action.quality_score == 8.5
    
    def test_weekly_calendar_creation(self):
        """Test creating a WeeklyCalendar object."""
        calendar = WeeklyCalendar(
            week_index=1,
            company_id="c1",
            actions=[],
        )
        
        assert calendar.week_index == 1
        assert len(calendar.actions) == 0
    
    def test_weekly_target_creation(self):
        """Test creating a WeeklyTarget object."""
        target = WeeklyTarget(
            total_actions=10,
            new_post_share=0.4,
            comment_share=0.6,
            per_subreddit_quota={"r/test": 3},
            per_persona_quota={"p1": 5},
            per_pillar_quota={"problems": 2},
        )
        
        assert target.total_actions == 10
        assert target.new_post_share == 0.4
        assert target.per_subreddit_quota["r/test"] == 3
    
    def test_evaluation_report_creation(self):
        """Test creating an EvaluationReport object."""
        report = EvaluationReport(
            overall_score=7.5,
            authenticity_score=8.0,
            diversity_score=7.0,
            cadence_score=7.5,
            alignment_score=7.5,
            warnings=["Test warning"],
        )
        
        assert report.overall_score == 7.5
        assert len(report.warnings) == 1


class TestHistoryModel:
    """Tests for history data model."""
    
    def test_posting_history_entry_creation(self):
        """Test creating a PostingHistoryEntry object."""
        entry = PostingHistoryEntry(
            date="2024-01-15",
            subreddit_name="r/test",
            persona_id="p1",
            topic="Test topic",
            pillar_id="problems",
            week_index=1,
        )
        
        assert entry.date == "2024-01-15"
        assert entry.week_index == 1
    
    def test_posting_history_entry_defaults(self):
        """Test PostingHistoryEntry default values."""
        entry = PostingHistoryEntry(
            date="2024-01-15",
            subreddit_name="r/test",
            persona_id="p1",
            topic="Test",
            pillar_id="p",
        )
        
        assert entry.week_index == 1

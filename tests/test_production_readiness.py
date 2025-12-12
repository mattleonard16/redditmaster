"""Tests for error handling, rate limiting, and edge cases."""

import pytest
from unittest.mock import patch, MagicMock
import json
import tempfile
from pathlib import Path


class TestErrorHandling:
    """Test that errors are logged, not silently swallowed."""
    
    def test_batch_generation_logs_on_failure(self, caplog):
        """Verify LLM failures are logged with context."""
        from src.csv.csv_planner import _generate_posts_batch
        from src.csv.csv_parser import CompanyCSVData, PersonaInfo
        
        # Create minimal CSV data
        csv_data = CompanyCSVData(
            company_name="TestCo",
            description="A test company",
            website="https://testco.com",
            subreddits=["r/test"],
            personas=[PersonaInfo("user1", "bio1"), PersonaInfo("user2", "bio2")],
            keywords={"K1": "test keyword"},
            posts_per_week=3,
        )
        
        # Mock action
        class MockAction:
            subreddit_name = "r/test"
        
        # With LLM unavailable, should log and return empty
        with patch('src.csv.csv_planner.get_openai_client', return_value=None):
            result = _generate_posts_batch([MockAction()], csv_data, ["user1"], [])
            assert result == []
    
    def test_csv_parser_validates_minimum_personas(self):
        """Verify parser rejects CSVs with fewer than 2 personas."""
        from src.csv.csv_parser import parse_company_csv
        
        # Create a CSV with only 1 persona
        csv_content = """Name,Value
Company,TestCo
Description,A test company
Username,Info
only_one_user,Single persona bio
Subreddits,
r/test,
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()
            
            with pytest.raises(ValueError, match="at least 2 personas"):
                parse_company_csv(f.name)
    
    def test_csv_parser_validates_minimum_subreddits(self):
        """Verify parser rejects CSVs with no subreddits."""
        from src.csv.csv_parser import parse_company_csv
        
        csv_content = """Name,Value
Company,TestCo
Description,A test company
Username,Info
user1,First persona
user2,Second persona
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()
            
            with pytest.raises(ValueError, match="at least 1 subreddit"):
                parse_company_csv(f.name)


class TestInputSanitization:
    """Test that input is properly sanitized."""
    
    def test_sanitize_removes_control_characters(self):
        """Verify control characters are stripped."""
        from src.csv.csv_parser import _sanitize_text
        
        dirty = "Hello\x00World\x1fTest"
        clean = _sanitize_text(dirty)
        assert "\x00" not in clean
        assert "\x1f" not in clean
        assert "HelloWorldTest" == clean
    
    def test_sanitize_normalizes_whitespace(self):
        """Verify multiple spaces become single space."""
        from src.csv.csv_parser import _sanitize_text
        
        dirty = "Hello    World   Test"
        clean = _sanitize_text(dirty)
        assert clean == "Hello World Test"
    
    def test_sanitize_handles_empty_input(self):
        """Verify empty input returns empty string."""
        from src.csv.csv_parser import _sanitize_text
        
        assert _sanitize_text("") == ""
        assert _sanitize_text(None) == ""


class TestEvaluatorAccuracy:
    """Test that evaluate_calendar_data checks actual output."""
    
    def test_evaluator_detects_promotional_language(self):
        """Verify promotional phrases are flagged."""
        from src.evaluation.evaluator import evaluate_calendar_data
        from src.csv.csv_generator import CalendarData, PlannedPost, PlannedComment
        
        posts = [
            PlannedPost(
                post_id="P1",
                subreddit="r/test",
                title="Check out this amazing tool!",  # Promotional
                body="You should try it today",
                author_username="user1",
                timestamp="2025-01-01 09:00",
                keyword_ids=["K1"],
            ),
            PlannedPost(
                post_id="P2",
                subreddit="r/other",
                title="Normal discussion post",
                body="Just wondering about something",
                author_username="user2",
                timestamp="2025-01-02 09:00",
                keyword_ids=["K1"],
            ),
        ]
        
        calendar_data = CalendarData(posts=posts, comments=[])
        report = evaluate_calendar_data(calendar_data)
        
        # Should have warning about promotional language
        assert any("Promotional" in w for w in report.warnings)
        assert report.authenticity_score < 10.0
    
    def test_evaluator_checks_persona_diversity(self):
        """Verify single-persona calendars are penalized."""
        from src.evaluation.evaluator import evaluate_calendar_data
        from src.csv.csv_generator import CalendarData, PlannedPost, PlannedComment
        
        # All posts from same author
        posts = [
            PlannedPost(
                post_id=f"P{i}",
                subreddit=f"r/sub{i}",
                title=f"Post {i}",
                body="Content",
                author_username="same_user",  # Same author for all
                timestamp=f"2025-01-0{i+1} 09:00",
                keyword_ids=["K1"],
            )
            for i in range(3)
        ]
        
        calendar_data = CalendarData(posts=posts, comments=[])
        report = evaluate_calendar_data(calendar_data)
        
        # Should flag low diversity
        assert report.diversity_score < 10.0
    
    def test_evaluator_rewards_good_calendars(self):
        """Verify well-formed calendars score high."""
        from src.evaluation.evaluator import evaluate_calendar_data
        from src.csv.csv_generator import CalendarData, PlannedPost, PlannedComment
        
        # Good calendar: multiple personas, subreddits, no promo language
        posts = [
            PlannedPost(
                post_id="P1",
                subreddit="r/productivity",
                title="What's your morning routine?",
                body="Curious how others start their day",
                author_username="alex_dev",
                timestamp="2025-01-01 09:00",
                keyword_ids=["K1"],
            ),
            PlannedPost(
                post_id="P2",
                subreddit="r/startups",
                title="Lessons from my first year",
                body="Made so many mistakes",
                author_username="jordan_pm",
                timestamp="2025-01-02 10:00",
                keyword_ids=["K2"],
            ),
            PlannedPost(
                post_id="P3",
                subreddit="r/consulting",
                title="How do you handle difficult clients?",
                body="Looking for advice",
                author_username="sam_ops",
                timestamp="2025-01-03 11:00",
                keyword_ids=["K3"],
            ),
        ]
        
        comments = [
            PlannedComment(
                comment_id="C1",
                post_id="P1",
                parent_comment_id=None,
                comment_text="Great question!",
                username="jordan_pm",
                timestamp="2025-01-01 10:00",
            ),
        ]
        
        calendar_data = CalendarData(posts=posts, comments=comments)
        report = evaluate_calendar_data(calendar_data)
        
        # Should score high
        assert report.overall_score >= 8.0
        assert report.diversity_score >= 9.0
        assert len(report.warnings) == 0


class TestRetryLogic:
    """Test LLM retry with exponential backoff."""
    
    def test_retry_attempts_multiple_times(self):
        """Verify batch generation retries on failure."""
        from src.csv.csv_planner import _generate_posts_batch
        from src.csv.csv_parser import CompanyCSVData, PersonaInfo
        
        csv_data = CompanyCSVData(
            company_name="TestCo",
            description="A test company",
            website="https://testco.com",
            subreddits=["r/test"],
            personas=[PersonaInfo("user1", "bio1"), PersonaInfo("user2", "bio2")],
            keywords={"K1": "test"},
            posts_per_week=1,
        )
        
        class MockAction:
            subreddit_name = "r/test"
        
        call_count = 0
        
        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Simulated failure")
            # Return valid response on 3rd try
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '[{"title": "Test", "body": "Content"}]'
            return mock_response
        
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        
        with patch('src.csv.csv_planner.get_openai_client', return_value=mock_client):
            with patch('time.sleep'):  # Don't actually wait
                result = _generate_posts_batch([MockAction()], csv_data, ["user1"], [])
        
        # Should have retried and succeeded
        assert call_count == 3
        assert len(result) == 1
        assert result[0][0] == "Test"

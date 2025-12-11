"""Tests for the CSV module - parsing and generation."""

import os
import tempfile
from pathlib import Path

import pytest

from src.csv.csv_parser import (
    parse_company_csv,
    PersonaInfo,
    CompanyCSVData,
    extract_keywords_for_topic,
)
from src.csv.csv_generator import (
    PlannedPost,
    PlannedComment,
    CalendarData,
    generate_calendar_csv,
    format_timestamp,
)
from src.csv.csv_planner import generate_calendar_from_csv


# Path to sample CSV
SAMPLE_CSV = Path(__file__).parent.parent / "SlideForge - Company Info.csv"


class TestCSVParser:
    """Tests for parsing company info CSVs."""
    
    @pytest.mark.skipif(not SAMPLE_CSV.exists(), reason="Sample CSV not present")
    def test_parse_slideforge_csv(self):
        """Test parsing the SlideForge company info CSV."""
        data = parse_company_csv(str(SAMPLE_CSV))
        
        # Check basic metadata
        assert "slideforge" in data.website.lower()
        assert len(data.description) > 100
        assert data.posts_per_week == 3
        
        # Check subreddits
        assert len(data.subreddits) > 0
        assert any("PowerPoint" in s for s in data.subreddits)
        
        # Check personas
        assert len(data.personas) >= 2  # At least 2 personas required
        persona_usernames = [p.username for p in data.personas]
        assert "riley_ops" in persona_usernames
        assert "jordan_consults" in persona_usernames
        
        # Check keywords
        assert len(data.keywords) > 0
        assert "K1" in data.keywords
    
    @pytest.mark.skipif(not SAMPLE_CSV.exists(), reason="Sample CSV not present")
    def test_persona_role_inference(self):
        """Test that persona roles are inferred from bios."""
        data = parse_company_csv(str(SAMPLE_CSV))
        
        # Find riley_ops - should be operations role
        riley = next((p for p in data.personas if p.username == "riley_ops"), None)
        assert riley is not None
        assert riley.role == "operations"
        
        # Find jordan_consults - should be consultant role
        jordan = next((p for p in data.personas if p.username == "jordan_consults"), None)
        assert jordan is not None
        assert jordan.role == "consultant"
    
    def test_keyword_extraction(self):
        """Test keyword matching for topics."""
        keywords = {
            "K1": "best ai presentation maker",
            "K2": "ai slide deck tool",
            "K3": "pitch deck generator",
        }
        
        # Test matching
        topic = "What is the best AI presentation maker for startups?"
        matched = extract_keywords_for_topic(topic, keywords)
        assert "K1" in matched  # Should match "best ai presentation maker"
        
        # Test with slide-related topic
        topic2 = "Need help with slide deck creation"
        matched2 = extract_keywords_for_topic(topic2, keywords)
        assert len(matched2) > 0  # Should match something
    
    def test_empty_keywords(self):
        """Test handling of empty keyword dict."""
        matched = extract_keywords_for_topic("some topic", {})
        assert matched == []


class TestCSVGenerator:
    """Tests for generating calendar CSVs."""
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        assert format_timestamp("2025-12-08", "morning") == "2025-12-08 9:03"
        assert format_timestamp("2025-12-08", "afternoon") == "2025-12-08 14:12"
        assert format_timestamp("2025-12-08", "evening") == "2025-12-08 18:44"
    
    def test_generate_simple_calendar(self):
        """Test generating a simple calendar CSV."""
        posts = [
            PlannedPost(
                post_id="P1",
                subreddit="r/test",
                title="Test Title",
                body="Test body content",
                author_username="testuser",
                timestamp="2025-12-08 14:12",
                keyword_ids=["K1", "K2"],
            )
        ]
        comments = [
            PlannedComment(
                comment_id="C1",
                post_id="P1",
                parent_comment_id=None,
                comment_text="Great post!",
                username="commenter",
                timestamp="2025-12-08 14:30",
            )
        ]
        
        calendar = CalendarData(posts=posts, comments=comments)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            generate_calendar_csv(calendar, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            
            # Read and verify content
            with open(output_path, 'r') as f:
                content = f.read()
            
            assert "post_id" in content
            assert "P1" in content
            assert "Test Title" in content
            assert "comment_id" in content
            assert "C1" in content
            assert "Great post!" in content
        finally:
            os.unlink(output_path)
    
    def test_comment_threading(self):
        """Test that nested comments have proper parent IDs."""
        posts = [
            PlannedPost(
                post_id="P1",
                subreddit="r/test",
                title="Test",
                body="Body",
                author_username="user1",
                timestamp="2025-12-08 14:12",
                keyword_ids=[],
            )
        ]
        comments = [
            PlannedComment(
                comment_id="C1",
                post_id="P1",
                parent_comment_id=None,  # Top-level
                comment_text="First comment",
                username="user2",
                timestamp="2025-12-08 14:20",
            ),
            PlannedComment(
                comment_id="C2",
                post_id="P1",
                parent_comment_id="C1",  # Reply to C1
                comment_text="Reply to first",
                username="user3",
                timestamp="2025-12-08 14:25",
            ),
        ]
        
        calendar = CalendarData(posts=posts, comments=comments)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            generate_calendar_csv(calendar, output_path)
            
            with open(output_path, 'r') as f:
                content = f.read()
            
            # C2 should reference C1 as parent
            assert "C2,P1,C1" in content
        finally:
            os.unlink(output_path)


class TestCSVPlanner:
    """Tests for the end-to-end CSV planner."""
    
    @pytest.mark.skipif(not SAMPLE_CSV.exists(), reason="Sample CSV not present")
    def test_generate_calendar_from_csv(self):
        """Test generating a calendar from the sample CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            calendar, evaluation = generate_calendar_from_csv(
                company_csv=str(SAMPLE_CSV),
                output_csv=output_path,
                week_index=1,
                use_llm=False,  # Use templates for deterministic tests
            )
            
            # Should have 3 posts (from posts_per_week)
            assert len(calendar.posts) == 3
            
            # Should have comments for each post (1-3 each)
            assert len(calendar.comments) >= 3
            assert len(calendar.comments) <= 9  # Max 3 per post
            
            # Evaluation should be reasonable
            assert evaluation.overall_score >= 5.0
        finally:
            os.unlink(output_path)
    
    @pytest.mark.skipif(not SAMPLE_CSV.exists(), reason="Sample CSV not present")
    def test_persona_rotation_in_posts(self):
        """Test that posts are authored by different personas."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            calendar, _ = generate_calendar_from_csv(
                company_csv=str(SAMPLE_CSV),
                output_csv=output_path,
                week_index=1,
                use_llm=False,
            )
            
            # Get unique authors
            post_authors = [p.author_username for p in calendar.posts]
            unique_authors = set(post_authors)
            
            # With 3 posts and 5 personas, we should have 3 different authors
            assert len(unique_authors) == len(calendar.posts), \
                f"Expected {len(calendar.posts)} unique authors, got {len(unique_authors)}: {post_authors}"
        finally:
            os.unlink(output_path)
    
    @pytest.mark.skipif(not SAMPLE_CSV.exists(), reason="Sample CSV not present")
    def test_no_self_reply_in_comments(self):
        """Test that post authors don't reply to their own posts."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            calendar, _ = generate_calendar_from_csv(
                company_csv=str(SAMPLE_CSV),
                output_csv=output_path,
                week_index=1,
                use_llm=False,
            )
            
            # Build a map of post_id -> author
            post_authors = {p.post_id: p.author_username for p in calendar.posts}
            
            # Check that no comment is from the post's author
            for comment in calendar.comments:
                post_author = post_authors.get(comment.post_id)
                assert comment.username != post_author, \
                    f"Comment {comment.comment_id} by {comment.username} is on their own post {comment.post_id}"
        finally:
            os.unlink(output_path)
    
    @pytest.mark.skipif(not SAMPLE_CSV.exists(), reason="Sample CSV not present")  
    def test_csv_structure_matches_sample(self):
        """Test that output CSV has correct structure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            generate_calendar_from_csv(
                company_csv=str(SAMPLE_CSV),
                output_csv=output_path,
                week_index=1,
                use_llm=False,
            )
            
            with open(output_path, 'r') as f:
                content = f.read()
            
            # Check for expected headers
            assert "post_id,subreddit,title,body,author_username,timestamp,keyword_ids" in content
            assert "comment_id,post_id,parent_comment_id" in content
            
            # Check for post and comment IDs
            assert "P1," in content
            assert "C1," in content
        finally:
            os.unlink(output_path)


class TestPersonaInfo:
    """Tests for PersonaInfo dataclass."""
    
    def test_role_inference_operations(self):
        """Test operations role inference."""
        persona = PersonaInfo(
            username="test_ops",
            bio="I am the head of operations at a startup."
        )
        assert persona.role == "operations"
    
    def test_role_inference_consultant(self):
        """Test consultant role inference."""
        persona = PersonaInfo(
            username="test_consultant",
            bio="I am an independent consultant working with founders."
        )
        assert persona.role == "consultant"
    
    def test_role_inference_student(self):
        """Test student role inference."""
        persona = PersonaInfo(
            username="test_student",
            bio="I am a senior majoring in computer science."
        )
        assert persona.role == "student"
    
    def test_stance_inference_advocate(self):
        """Test advocate stance inference."""
        persona = PersonaInfo(
            username="happy_user",
            bio="The breakthrough came when I tried this tool. It finally worked!"
        )
        assert persona.stance == "advocate"
    
    def test_expertise_inference_expert(self):
        """Test expert expertise level inference."""
        persona = PersonaInfo(
            username="senior_dev",
            bio="I am the head of engineering with 15 years experience."
        )
        assert persona.expertise_level == "expert"
    
    def test_expertise_inference_novice(self):
        """Test novice expertise level inference."""
        persona = PersonaInfo(
            username="new_user",
            bio="I am a first-time founder just getting started."
        )
        assert persona.expertise_level == "novice"

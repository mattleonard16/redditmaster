"""CSV generator for content calendar files following the SlideForge format."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PlannedPost:
    """A planned Reddit post for the CSV output."""
    post_id: str          # P1, P2, P3...
    subreddit: str        # r/PowerPoint
    title: str            # Generated title
    body: str             # Generated body
    author_username: str  # riley_ops
    timestamp: str        # 2025-12-08 14:12
    keyword_ids: List[str]  # [K1, K14, K4]


@dataclass
class PlannedComment:
    """A planned Reddit comment for the CSV output."""
    comment_id: str       # C1, C2, C3...
    post_id: str          # Which post this belongs to
    parent_comment_id: Optional[str]  # For nested replies, None for top-level
    comment_text: str     # Generated comment body
    username: str         # jordan_consults
    timestamp: str        # 2025-12-08 14:33


@dataclass
class CalendarData:
    """Complete calendar data for CSV output."""
    posts: List[PlannedPost]
    comments: List[PlannedComment]


def generate_calendar_csv(
    calendar_data: CalendarData,
    filepath: str,
) -> None:
    """Generate a content calendar CSV matching the SlideForge format.
    
    The CSV structure:
    1. Empty header row
    2. Posts table header: post_id, subreddit, title, body, author_username, timestamp, keyword_ids
    3. Post rows (P1, P2, ...)
    4. Empty separator rows
    5. Comments table header: comment_id, post_id, parent_comment_id, comment_text, username, timestamp
    6. Comment rows (C1, C2, ...)
    
    Args:
        calendar_data: The posts and comments to write
        filepath: Output CSV file path
    """
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Empty header row (7 columns to match format)
        writer.writerow(['', '', '', '', '', '', ''])
        
        # Posts table header
        writer.writerow([
            'post_id', 'subreddit', 'title', 'body', 
            'author_username', 'timestamp', 'keyword_ids'
        ])
        
        # Post rows
        for post in calendar_data.posts:
            keyword_str = ", ".join(post.keyword_ids)
            writer.writerow([
                post.post_id,
                post.subreddit,
                post.title,
                post.body,
                post.author_username,
                post.timestamp,
                keyword_str,
            ])
        
        # Empty separator rows
        for _ in range(5):
            writer.writerow(['', '', '', '', '', '', ''])
        
        # Comments table header
        writer.writerow([
            'comment_id', 'post_id', 'parent_comment_id', 
            'comment_text', 'username', 'timestamp', ''
        ])
        
        # Comment rows
        for comment in calendar_data.comments:
            writer.writerow([
                comment.comment_id,
                comment.post_id,
                comment.parent_comment_id or '',
                comment.comment_text,
                comment.username,
                comment.timestamp,
                '',  # Extra column to match format
            ])


def format_timestamp(date_str: str, time_slot: str) -> str:
    """Convert date + time_slot to timestamp format.
    
    Args:
        date_str: ISO date string (YYYY-MM-DD)
        time_slot: morning, afternoon, or evening
        
    Returns:
        Formatted timestamp like "2025-12-08 14:12"
    """
    time_map = {
        "morning": "9:03",
        "afternoon": "14:12",
        "evening": "18:44",
    }
    time_part = time_map.get(time_slot, "12:00")
    return f"{date_str.replace('-', '-')} {time_part}"

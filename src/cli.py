#!/usr/bin/env python3
"""Command-line interface for the Reddit Mastermind Planner."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src to path if needed
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path.parent))

from src.models import PostingHistoryEntry
from src.planning.calendar import generate_content_calendar
from src.config.companies import get_config_by_name, list_configs


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate weekly content calendars for Reddit growth.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a simple week 1 calendar
  python -m src.cli
  
  # Generate 15 posts for week 3
  python -m src.cli --posts 15 --week 3
  
  # Use a different company config
  python -m src.cli --config devtools
  
  # List available configs
  python -m src.cli --list-configs
  
  # Start from a specific date
  python -m src.cli --start-date 2024-01-15
  
  # Output as JSON
  python -m src.cli --format json --output calendar.json
  
  # Show detailed prompt briefs
  python -m src.cli --verbose
        """,
    )
    
    # Calendar parameters
    parser.add_argument(
        "--posts", "-n",
        type=int,
        default=10,
        help="Number of posts per week (default: 10)",
    )
    parser.add_argument(
        "--week", "-w",
        type=int,
        default=1,
        help="Week index (default: 1)",
    )
    parser.add_argument(
        "--start-date", "-s",
        type=str,
        default=None,
        help="Start date for the week (YYYY-MM-DD format)",
    )
    
    # Output options
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information including prompt briefs",
    )
    
    # Advanced options
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="slideforge",
        help=f"Company config to use (default: slideforge). Options: {', '.join(list_configs())}",
    )
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List available company configurations and exit",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM-based idea generation (faster, deterministic)",
    )
    parser.add_argument(
        "--history-file",
        type=str,
        default=None,
        help="JSON file containing posting history",
    )
    
    args = parser.parse_args()
    
    # Handle list-configs
    if args.list_configs:
        print("Available configurations:")
        for config in list_configs():
            print(f"  - {config}")
        sys.exit(0)
    
    # Parse start date if provided
    start_date: Optional[datetime] = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            print(f"Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
    
    # Load history if provided
    history: List[PostingHistoryEntry] = []
    if args.history_file:
        history = load_history_from_file(args.history_file)
    
    # Load configuration
    try:
        company, personas, subreddits, templates = get_config_by_name(args.config)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Generate calendar
    print(f"Generating calendar for {company.name}...", file=sys.stderr)
    print(f"Week {args.week} | {args.posts} posts | LLM: {'enabled' if not args.no_llm else 'disabled'}", file=sys.stderr)
    
    calendar, evaluation = generate_content_calendar(
        company=company,
        personas=personas,
        subreddits=subreddits,
        templates=templates,
        num_posts_per_week=args.posts,
        history=history,
        week_index=args.week,
        start_date=start_date,
        use_llm=not args.no_llm,
    )
    
    # Format output
    if args.format == "json":
        output = format_json(calendar, evaluation, verbose=args.verbose)
    else:
        output = format_text(calendar, evaluation, verbose=args.verbose)
    
    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Calendar saved to {args.output}", file=sys.stderr)
    else:
        print(output)


def format_text(calendar, evaluation, verbose: bool = False) -> str:
    """Format calendar as human-readable text."""
    lines = []
    lines.append(f"=== Week {calendar.week_index} Calendar ===")
    lines.append(f"Total actions: {len(calendar.actions)}")
    lines.append("")
    
    for action in calendar.actions:
        lines.append(f"{action.date} ({action.time_slot})")
        lines.append(f"  Subreddit: {action.subreddit_name}")
        lines.append(f"  Persona: {action.persona_id}")
        lines.append(f"  Type: {action.post_type}")
        lines.append(f"  Score: {action.quality_score:.1f}")
        
        # Show threading info if present
        if action.thread_id:
            lines.append(f"  Thread: {action.thread_id[:8]}...")
        if action.parent_action_id:
            lines.append(f"  Reply to: {action.parent_action_id[:8]}...")
        
        if verbose and action.prompt_brief:
            lines.append(f"  Prompt Brief:")
            for brief_line in action.prompt_brief.split("\n"):
                lines.append(f"    {brief_line}")
        lines.append("")
    
    lines.append("=== Evaluation ===")
    lines.append(f"Overall: {evaluation.overall_score:.1f}/10")
    lines.append(f"  Authenticity: {evaluation.authenticity_score:.1f}")
    lines.append(f"  Diversity: {evaluation.diversity_score:.1f}")
    lines.append(f"  Cadence: {evaluation.cadence_score:.1f}")
    lines.append(f"  Alignment: {evaluation.alignment_score:.1f}")
    
    if evaluation.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in evaluation.warnings:
            lines.append(f"  - {warning}")
    
    return "\n".join(lines)


def format_json(calendar, evaluation, verbose: bool = False) -> str:
    """Format calendar as JSON."""
    data = {
        "week_index": calendar.week_index,
        "company_id": calendar.company_id,
        "actions": [
            {
                "id": action.id,
                "date": action.date,
                "time_slot": action.time_slot,
                "subreddit_name": action.subreddit_name,
                "persona_id": action.persona_id,
                "post_type": action.post_type,
                "content_idea_id": action.content_idea_id,
                "quality_score": action.quality_score,
                "thread_id": action.thread_id,
                "parent_action_id": action.parent_action_id,
                **({"prompt_brief": action.prompt_brief} if verbose else {}),
            }
            for action in calendar.actions
        ],
        "evaluation": {
            "overall_score": evaluation.overall_score,
            "authenticity_score": evaluation.authenticity_score,
            "diversity_score": evaluation.diversity_score,
            "cadence_score": evaluation.cadence_score,
            "alignment_score": evaluation.alignment_score,
            "warnings": evaluation.warnings,
        },
    }
    return json.dumps(data, indent=2)


def load_history_from_file(filepath: str) -> List[PostingHistoryEntry]:
    """Load posting history from a JSON file."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        
        history = []
        for entry in data:
            history.append(PostingHistoryEntry(
                date=entry.get("date", ""),
                subreddit_name=entry.get("subreddit_name", ""),
                persona_id=entry.get("persona_id", ""),
                topic=entry.get("topic", ""),
                pillar_id=entry.get("pillar_id", ""),
                week_index=entry.get("week_index", 0),
            ))
        return history
        
    except FileNotFoundError:
        print(f"Warning: History file '{filepath}' not found. Starting fresh.", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in '{filepath}': {e}. Starting fresh.", file=sys.stderr)
        return []


def csv_main():
    """CSV mode entry point."""
    parser = argparse.ArgumentParser(
        description="Generate content calendar from CSV company info.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate calendar from company CSV
  python -m src.cli csv --company company_info.csv --output calendar.csv
  
  # Disable LLM for faster deterministic output
  python -m src.cli csv --company company_info.csv --output calendar.csv --no-llm
        """,
    )
    
    parser.add_argument(
        "--company", "-c",
        type=str,
        required=True,
        help="Path to company info CSV file",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        required=True,
        help="Path for output calendar CSV file",
    )
    parser.add_argument(
        "--week", "-w",
        type=int,
        default=1,
        help="Week index (default: 1)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM for content generation (faster, less varied)",
    )
    
    args = parser.parse_args(sys.argv[2:])  # Skip 'csv' subcommand
    
    # Import CSV module
    from src.csv.csv_planner import generate_calendar_from_csv
    
    print(f"Parsing company info from {args.company}...", file=sys.stderr)
    print(f"Week {args.week} | LLM: {'disabled' if args.no_llm else 'enabled'}", file=sys.stderr)
    
    try:
        calendar_data, evaluation = generate_calendar_from_csv(
            company_csv=args.company,
            output_csv=args.output,
            week_index=args.week,
            use_llm=not args.no_llm,
        )
        
        print(f"\nGenerated:", file=sys.stderr)
        print(f"  Posts: {len(calendar_data.posts)}", file=sys.stderr)
        print(f"  Comments: {len(calendar_data.comments)}", file=sys.stderr)
        print(f"  Evaluation: {evaluation.overall_score:.1f}/10", file=sys.stderr)
        print(f"\nCalendar saved to {args.output}", file=sys.stderr)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating calendar: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Check for subcommands
    if len(sys.argv) > 1 and sys.argv[1] == "csv":
        csv_main()
    else:
        main()

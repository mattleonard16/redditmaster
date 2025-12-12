"""
The Reddit Mastermind - Content Calendar Planning Algorithm

Demonstrates automated content calendar generation for Reddit growth.
Shows natural conversations, persona rotation, and quality evaluation.
"""

import io
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

# Must be first Streamlit command
st.set_page_config(
    page_title="The Reddit Mastermind",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Import after page config
from src.csv.csv_parser import parse_company_csv
from src.csv.csv_planner import generate_calendar_from_csv
from src.csv.csv_generator import CalendarData
from src.models import PostingHistoryEntry

# Sample CSV path
SAMPLE_CSV = Path(__file__).parent / "SlideForge - Company Info.csv"


def load_sample_csv():
    """Load the bundled SlideForge sample CSV."""
    if SAMPLE_CSV.exists():
        return SAMPLE_CSV.read_bytes()
    return None


def main():
    """Main Streamlit app."""
    
    # Header
    st.title("The Reddit Mastermind")
    st.markdown(
        """
        **The Problem:** Creating weekly Reddit content calendars by hand takes hours.  
        **The Solution:** This algorithm automates the entire planning process.
        
        ---
        """
    )
    
    # Main content area - simpler layout
    st.subheader("Input: Company Info")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload CSV or use sample below",
            type=["csv"],
            help="CSV with company info, personas (2+), subreddits, and keywords"
        )
        
        # Handle sample data
        if st.session_state.get('sample_loaded') and not uploaded_file:
            uploaded_file = st.session_state.get('sample_data')
            st.info("Using SlideForge sample data")
    
    with col2:
        # Load Sample button
        if SAMPLE_CSV.exists():
            st.markdown("**Try the demo:**")
            if st.button("Load SlideForge Sample", use_container_width=True, type="secondary"):
                sample_data = load_sample_csv()
                if sample_data:
                    st.session_state['sample_loaded'] = True
                    st.session_state['sample_data'] = sample_data
                    st.rerun()
    
    # Parse and show preview
    parsed_data = None
    tmp_path = None
    
    if uploaded_file is not None:
        st.markdown("---")
        st.subheader("Parsed Inputs")
        try:
            # Handle both file upload and bytes
            if hasattr(uploaded_file, 'getvalue'):
                file_content = uploaded_file.getvalue()
            else:
                file_content = uploaded_file
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            
            # Parse to show preview
            csv_data = parse_company_csv(tmp_path)
            parsed_data = csv_data
            
            # Summary metrics
            summary_cols = st.columns(4)
            with summary_cols[0]:
                st.metric("Posts/Week", csv_data.posts_per_week)
            with summary_cols[1]:
                st.metric("Personas", len(csv_data.personas))
            with summary_cols[2]:
                st.metric("Subreddits", len(csv_data.subreddits))
            with summary_cols[3]:
                st.metric("Keywords", len(csv_data.keywords))
            
            # Show personas and subreddits
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.caption(f"**Personas:** {', '.join([p.username for p in csv_data.personas])}")
            with detail_col2:
                st.caption(f"**Subreddits:** {', '.join(csv_data.subreddits)}")
            
            # Validation warnings
            warnings = []
            if len(csv_data.personas) < 2:
                warnings.append("Need at least 2 personas for threaded conversations")
            if len(csv_data.subreddits) < 1:
                warnings.append("No subreddits found")
            if csv_data.posts_per_week < 1:
                warnings.append("Posts per week should be at least 1")
            
            if warnings:
                for w in warnings:
                    st.warning(w)
            
            # Store for generation
            st.session_state['tmp_path'] = tmp_path
            st.session_state['csv_data'] = csv_data
            # Reset multi-week history when a new company CSV is uploaded
            st.session_state['history_entries'] = []
            
        except Exception as e:
            st.error(f"Error parsing CSV: {str(e)}")
            parsed_data = None
    
    # Generate section
    if uploaded_file is not None and parsed_data:
        st.markdown("---")
        st.subheader("Generate Calendar")
        
        gen_col1, gen_col2, gen_col3 = st.columns([2, 1, 1])
        
        with gen_col1:
            # Week selection
            week_to_generate = st.session_state.get('next_week', 1)
            st.markdown(f"**Generate Week:** {week_to_generate}")
        
        with gen_col2:
            st.markdown("")  # Spacer
        
        with gen_col3:
            # Generate button
            if st.button("Generate Calendar", type="primary", use_container_width=True):
                spinner_msg = f"Generating Week {week_to_generate} calendar... (LLM mode, please wait ~15-25s)"
                with st.spinner(spinner_msg):
                    # Generate calendar
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out_tmp:
                        out_path = out_tmp.name
                    
                    calendar_data, evaluation = generate_calendar_from_csv(
                        company_csv=st.session_state['tmp_path'],
                        output_csv=out_path,
                        week_index=week_to_generate,
                        use_llm=True,  # Always use LLM
                        history=st.session_state.get('history_entries', []),
                    )

                    # Append this week's posts into history for next-week generation
                    def _infer_pillar_id(title: str) -> str:
                        t = (title or "").lower()
                        if any(w in t for w in [" vs ", " versus ", "compare"]):
                            return "comparisons"
                        if t.startswith("how") or " how to " in t or "guide" in t:
                            return "howto"
                        if any(w in t for w in ["worked", "results", "case study", "what happened"]):
                            return "case_studies"
                        if any(w in t for w in ["unpopular", "hot take", "opinion"]):
                            return "opinions"
                        return "problems"

                    history_entries = list(st.session_state.get('history_entries', []))
                    for post in calendar_data.posts:
                        date_part = post.timestamp.split(" ")[0] if post.timestamp else ""
                        history_entries.append(
                            PostingHistoryEntry(
                                date=date_part,
                                subreddit_name=post.subreddit,
                                persona_id=post.author_username,
                                topic=post.title,
                                pillar_id=_infer_pillar_id(post.title),
                                week_index=week_to_generate,
                                keyword_ids=list(post.keyword_ids or []),
                            )
                        )
                    st.session_state['history_entries'] = history_entries
                    
                    # Store in session state
                    st.session_state['calendar_data'] = calendar_data
                    st.session_state['evaluation'] = evaluation
                    st.session_state['out_path'] = out_path
                    st.session_state['company_name'] = st.session_state['csv_data'].company_name
                    st.session_state['week_index'] = week_to_generate
                    st.session_state['next_week'] = week_to_generate + 1
                    st.rerun()
    
    else:
        if not uploaded_file:
            st.info("Upload a company CSV or load the sample to get started")
    
    # Results section
    if 'calendar_data' in st.session_state:
        st.markdown("---")
        st.markdown("---")
        
        calendar_data = st.session_state['calendar_data']
        evaluation = st.session_state['evaluation']
        week = st.session_state.get('week_index', 1)
        csv_data = st.session_state.get('csv_data')
        
        # Header with quality score
        st.subheader(f"Output: Week {week} Calendar")
        
        # Main score with color
        score = evaluation.overall_score
        if score >= 8:
            score_label = "Excellent - Natural conversations, good distribution"
        elif score >= 6:
            score_label = "Good - Some minor issues"
        else:
            score_label = "Needs Review - Check warnings below"
        
        st.markdown(f"### Quality Score: {score:.1f}/10")
        st.caption(score_label)
        
        # Sub-scores in compact row
        score_cols = st.columns(4)
        with score_cols[0]:
            st.metric("Authenticity", f"{evaluation.authenticity_score:.1f}/10")
        with score_cols[1]:
            st.metric("Diversity", f"{evaluation.diversity_score:.1f}/10")
        with score_cols[2]:
            st.metric("Cadence", f"{evaluation.cadence_score:.1f}/10")
        with score_cols[3]:
            st.metric("Alignment", f"{evaluation.alignment_score:.1f}/10")
        
        # Warnings if any
        if evaluation.warnings:
            st.warning(f"**{len(evaluation.warnings)} Warning(s):**")
            for warning in evaluation.warnings:
                st.caption(f"• {warning}")
        
        # Summary stats
        unique_subreddits = set(p.subreddit for p in calendar_data.posts)
        unique_personas = set(p.author_username for p in calendar_data.posts)
        unique_personas.update(c.username for c in calendar_data.comments)
        
        st.markdown("---")
        
        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.markdown(f"**{len(calendar_data.posts)} Posts**")
        with stat_cols[1]:
            st.markdown(f"**{len(calendar_data.comments)} Comments**")
        with stat_cols[2]:
            st.markdown(f"**{len(unique_personas)} Personas Used**")
        with stat_cols[3]:
            st.markdown(f"**{len(unique_subreddits)} Subreddits**")
        
        st.markdown("---")
        
        # Show actual conversations to demonstrate quality
        st.subheader("Sample Conversations (to show they look natural)")
        
        tab1, tab2 = st.tabs(["Threaded View", "Download"])
        
        with tab1:
            # Show first few conversations as examples
            for i, post in enumerate(calendar_data.posts[:3]):  # Show first 3
                with st.container():
                    st.markdown(f"**[{post.subreddit}]** {post.title}")
                    st.caption(f"Posted by `{post.author_username}` • {post.timestamp}")
                    
                    # Show body preview
                    with st.expander("View post body"):
                        st.markdown(post.body)
                    
                    # Comments
                    post_comments = [c for c in calendar_data.comments if c.post_id == post.post_id]
                    if post_comments:
                        st.markdown("**Comments:**")
                        
                        # Build comment tree
                        top_level = [c for c in post_comments if not c.parent_comment_id]
                        
                        for comment in top_level:
                            # Show that author doesn't reply to own post
                            if comment.username == post.author_username:
                                st.error(f"SELF-REPLY DETECTED: {comment.username} replied to own post!")
                            else:
                                st.markdown(f"→ **`{comment.username}`**: {comment.comment_text}")
                            
                            # Show nested replies
                            for reply in post_comments:
                                if reply.parent_comment_id == comment.comment_id:
                                    if reply.username == comment.username:
                                        st.error(f"SELF-REPLY: {reply.username} replied to own comment!")
                                    else:
                                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└─ **`{reply.username}`**: {reply.comment_text}")
                    else:
                        st.caption("No comments for this post")
                    
                    st.divider()
            
            if len(calendar_data.posts) > 3:
                st.caption(f"Showing 3 of {len(calendar_data.posts)} posts. Download CSV to see all.")
        
        with tab2:
            download_col1, download_col2 = st.columns(2)
            
            with download_col1:
                # CSV download
                with open(st.session_state['out_path'], 'r') as f:
                    csv_content = f.read()
                
                company_name = st.session_state.get('company_name', 'calendar') or 'calendar'
                st.download_button(
                    label="Download CSV",
                    data=csv_content,
                    file_name=f"{company_name}_week{week}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            
            with download_col2:
                # JSON download
                json_data = {
                    "week_index": week,
                    "generated_at": datetime.now().isoformat(),
                    "evaluation": {
                        "overall_score": evaluation.overall_score,
                        "authenticity_score": evaluation.authenticity_score,
                        "diversity_score": evaluation.diversity_score,
                        "cadence_score": evaluation.cadence_score,
                        "alignment_score": evaluation.alignment_score,
                        "warnings": evaluation.warnings,
                    },
                    "posts": [
                        {
                            "post_id": p.post_id,
                            "subreddit": p.subreddit,
                            "title": p.title,
                            "body": p.body,
                            "author_username": p.author_username,
                            "timestamp": p.timestamp,
                            "keyword_ids": p.keyword_ids,
                        }
                        for p in calendar_data.posts
                    ],
                    "comments": [
                        {
                            "comment_id": c.comment_id,
                            "post_id": c.post_id,
                            "parent_comment_id": c.parent_comment_id,
                            "comment_text": c.comment_text,
                            "username": c.username,
                            "timestamp": c.timestamp,
                        }
                        for c in calendar_data.comments
                    ],
                }
                
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(json_data, indent=2),
                    file_name=f"{company_name}_week{week}.json",
                    mime="application/json",
                    use_container_width=True,
                )
        
        # Footer
        st.markdown("---")
        st.caption("Reddit Mastermind Planner - Generating realistic content calendars")


if __name__ == "__main__":
    main()

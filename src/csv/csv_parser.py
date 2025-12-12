"""CSV parser for company info files following the SlideForge format."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PersonaInfo:
    """Parsed persona information from company CSV."""
    username: str
    bio: str
    # Derived fields
    role: str = ""
    stance: str = "neutral"
    expertise_level: str = "intermediate"
    
    def __post_init__(self):
        """Derive role and stance from bio content."""
        bio_lower = self.bio.lower()
        
        # Infer role from bio
        if "operations" in bio_lower or "ops" in bio_lower:
            self.role = "operations"
        elif "consultant" in bio_lower or "freelance" in bio_lower:
            self.role = "consultant"
        elif "student" in bio_lower or "majoring" in bio_lower:
            self.role = "student"
        elif "sales" in bio_lower:
            self.role = "sales"
        elif "product manager" in bio_lower or "pm" in bio_lower:
            self.role = "product_manager"
        elif "founder" in bio_lower or "startup" in bio_lower:
            self.role = "founder"
        else:
            self.role = "professional"
        
        # Infer stance from bio (looking for positive/neutral signals)
        if "breakthrough" in bio_lower or "finally" in bio_lower or "changed" in bio_lower:
            self.stance = "advocate"
        elif "trying" in bio_lower or "unsure" in bio_lower:
            self.stance = "neutral"
        else:
            self.stance = "neutral"
        
        # Infer expertise
        if "head of" in bio_lower or "senior" in bio_lower or "expert" in bio_lower:
            self.expertise_level = "expert"
        elif "first-time" in bio_lower or "student" in bio_lower or "new to" in bio_lower:
            self.expertise_level = "novice"
        else:
            self.expertise_level = "intermediate"


@dataclass
class CompanyCSVData:
    """Parsed company data from CSV file."""
    website: str
    description: str
    subreddits: List[str]
    posts_per_week: int
    personas: List[PersonaInfo]
    keywords: Dict[str, str]  # keyword_id -> keyword phrase
    company_name: str = ""
    
    def __post_init__(self):
        """Extract company name from website."""
        if not self.company_name and self.website:
            # Extract from domain
            match = re.search(r'(\w+)\.\w+', self.website)
            if match:
                self.company_name = match.group(1).capitalize()


def parse_company_csv(filepath: str) -> CompanyCSVData:
    """Parse a company info CSV file following the SlideForge format.
    
    The CSV has two columns: Name and [CompanyName].
    Structure:
    - Metadata section: Website, Description, Subreddits, Number of posts per week
    - Persona section: Username header row, then username -> bio rows
    - Keyword section: keyword_id header row, then K1-K16 -> keyword phrase rows
    
    Args:
        filepath: Path to the company info CSV file
        
    Returns:
        CompanyCSVData with parsed information
        
    Raises:
        ValueError: If file is not a valid Company Info CSV
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        raise ValueError("CSV file is too short to contain company data")
    
    # Check if this is a Content Calendar (output) file instead of Company Info (input)
    first_data_row = rows[1] if len(rows) > 1 else []
    if len(first_data_row) > 0 and first_data_row[0].lower() in ['post_id', '']:
        # Check for calendar headers
        for row in rows[:5]:
            if len(row) > 0 and row[0] == 'post_id':
                raise ValueError(
                    "This appears to be a Content Calendar (output) file, not a Company Info (input) file. "
                    "Please upload a Company Info CSV that contains: Website, Description, Personas, and Keywords."
                )
    
    # Determine company name from header row
    header = rows[0]
    company_col_name = header[1] if len(header) > 1 else "Company"
    
    # Initialize data containers
    website = ""
    description = ""
    subreddits: List[str] = []
    posts_per_week = 10
    personas: List[PersonaInfo] = []
    keywords: Dict[str, str] = {}
    
    # Parse modes
    mode = "metadata"  # metadata, personas, keywords
    
    for row in rows[1:]:
        if len(row) < 2:
            continue
        
        name = row[0].strip()
        value = row[1].strip()
        
        # Skip empty rows
        if not name and not value:
            continue
        
        # Detect section changes
        if name == "Username" and value == "Info":
            mode = "personas"
            continue
        elif name == "keyword_id" and value == "keyword":
            mode = "keywords"
            continue
        
        # Parse based on mode
        if mode == "metadata":
            if name.lower() == "website":
                website = value
            elif name.lower() == "description":
                description = value
            elif name.lower() == "subreddits":
                # Parse newline-separated subreddits
                subreddits = [s.strip() for s in value.split("\n") if s.strip()]
            elif "posts per week" in name.lower():
                try:
                    posts_per_week = int(value)
                except ValueError:
                    posts_per_week = 10
        
        elif mode == "personas":
            if name and value and not name.startswith("keyword"):
                personas.append(PersonaInfo(username=name, bio=value))
        
        elif mode == "keywords":
            if name.upper().startswith("K") and value:
                keywords[name.upper()] = value
    
    # Validate required data
    if len(personas) < 2:
        raise ValueError(
            f"Company Info requires at least 2 personas, but only {len(personas)} found. "
            "Please ensure the CSV has a 'Username' / 'Info' section with at least 2 persona entries."
        )
    
    if len(subreddits) < 1:
        raise ValueError(
            "Company Info requires at least 1 subreddit, but none found. "
            "Please ensure the CSV has a 'Subreddits' field with target subreddits."
        )
    
    return CompanyCSVData(
        website=website,
        description=description,
        subreddits=subreddits,
        posts_per_week=posts_per_week,
        personas=personas,
        keywords=keywords,
        company_name=company_col_name if company_col_name != "Company" else "",
    )


def extract_keywords_for_topic(topic: str, keywords: Dict[str, str], max_keywords: int = 3) -> List[str]:
    """Match a topic to relevant keyword IDs.
    
    Args:
        topic: The topic or title text
        keywords: Dictionary of keyword_id -> keyword phrase
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of matching keyword IDs (e.g., ["K1", "K4", "K14"])
    """
    topic_lower = topic.lower()
    topic_words = set(topic_lower.split())
    
    scored_keywords = []
    for kid, phrase in keywords.items():
        phrase_lower = phrase.lower()
        phrase_words = set(phrase_lower.split())
        
        # Score by word overlap
        overlap = len(topic_words & phrase_words)
        
        # Bonus for substring match
        if phrase_lower in topic_lower or any(w in topic_lower for w in phrase_words if len(w) > 3):
            overlap += 2
        
        if overlap > 0:
            scored_keywords.append((kid, overlap))
    
    # Sort by score and take top matches
    scored_keywords.sort(key=lambda x: x[1], reverse=True)
    return [kid for kid, _ in scored_keywords[:max_keywords]]

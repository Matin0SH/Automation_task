"""
JSON schema definitions for parsed document output
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional
from datetime import datetime
import json


@dataclass
class DocumentMetadata:
    """Metadata about the parsing operation"""
    parsed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    topic_folder: str = ""
    file_count: int = 0
    missing_documents: list = field(default_factory=list)


@dataclass
class ParsedDocuments:
    """Container for all parsed documents"""
    product_roadmap: Optional[str] = None
    engineering_ticket: Optional[str] = None
    meeting_transcript: Optional[str] = None
    marketing_notes: Optional[str] = None
    customer_feedback: Optional[str] = None


@dataclass
class TopicData:
    """Complete topic data structure"""
    topic: str
    documents: ParsedDocuments
    metadata: DocumentMetadata

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# Document type identifiers - keywords to match in filenames
# Keywords are checked in priority order (most specific to least specific)
# Multi-word phrases are preferred over single words for accuracy
DOCUMENT_KEYWORDS = {
    'meeting_transcript': [
        'meeting transcript',  # Full phrase (most specific)
        'transcript',          # Fallback
    ],
    'marketing_notes': [
        'marketing & product',  # Full phrase
        'marketing notes',      # Multi-word
        'marketing note',       # Singular
        'product meeting',      # Alternative phrasing
    ],
    'product_roadmap': [
        'product roadmap summary',  # Full phrase
        'roadmap summary',          # Two words
        'product roadmap',          # Two words
        'roadmap',                  # Single word fallback
    ],
    'engineering_ticket': [
        'linear ticket',       # Two words
        'engineering ticket',  # Two words
        'linear',              # Single word (specific)
        'ticket',              # Single word fallback
    ],
    'customer_feedback': [
        'customer feedback',   # Two words
        'feedback snippet',    # Two words
        'feedback',            # Single word
    ]
}


def identify_document_type(filename: str) -> Optional[str]:
    """
    Identify document type based on filename keywords

    Checks keywords in priority order (most specific first) to avoid
    misclassification due to overlapping keywords.

    Args:
        filename: Name of the file

    Returns:
        Document type key or None if no match
    """
    filename_lower = filename.lower()

    # Priority order: check most specific document types first
    # This prevents "Meeting Transcript (Product + Engineering + Marketing).docx"
    # from being matched as 'product_roadmap' instead of 'meeting_transcript'
    priority_order = [
        'meeting_transcript',   # Most specific (contains "transcript")
        'marketing_notes',      # Specific (contains "marketing notes" or "marketing & product")
        'product_roadmap',      # Can contain "product" which is common
        'engineering_ticket',   # Specific (linear, engineering)
        'customer_feedback',    # Specific (feedback)
    ]

    for doc_type in priority_order:
        keywords = DOCUMENT_KEYWORDS[doc_type]
        # Check keywords in order (longer phrases first for each type)
        # Keywords are already sorted by specificity in DOCUMENT_KEYWORDS
        for keyword in keywords:
            if keyword in filename_lower:
                return doc_type

    return None

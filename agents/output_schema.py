"""
Output schema definitions for generated content

Mirrors the input schema structure for consistency
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import json
import google.generativeai as genai


@dataclass
class LinkedInPost:
    """LinkedIn post output structure"""
    content: str
    hashtags: List[str]


@dataclass
class NewsletterEmail:
    """Newsletter email output structure"""
    subject_line: str
    body: str


@dataclass
class BlogPost:
    """Blog post output structure"""
    title: str
    content: str


@dataclass
class GenerationMetadata:
    """Metadata about the generation process"""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    channel: str = ""
    final_score: float = 0.0
    passed_quality: bool = False
    refinement_iterations: int = 0
    refinement_history: List[dict] = field(default_factory=list)
    final_feedback: dict = field(default_factory=dict)
    model_used: str = ""


@dataclass
class GeneratedContent:
    """Container for generated content output"""
    topic: str
    channel: str
    linkedin_post: Optional[LinkedInPost] = None
    newsletter: Optional[NewsletterEmail] = None
    blog_post: Optional[BlogPost] = None
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {
            'topic': self.topic,
            'channel': self.channel,
        }

        # Add channel-specific content
        if self.linkedin_post:
            result['linkedin_post'] = asdict(self.linkedin_post)
        if self.newsletter:
            result['newsletter'] = asdict(self.newsletter)
        if self.blog_post:
            result['blog_post'] = asdict(self.blog_post)

        # Add metadata
        result['metadata'] = asdict(self.metadata)

        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_to_file(self, output_path: str) -> None:
        """Save to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    def to_markdown(self) -> str:
        """Convert to Markdown format for easy reading and sharing"""
        lines = []

        # Header
        lines.append(f"# {self.topic}")
        lines.append("")
        lines.append(f"**Channel:** {self.channel.upper()}")
        lines.append(f"**Generated:** {self.metadata.generated_at}")
        lines.append(f"**Quality Score:** {self.metadata.final_score}/10 {'✅' if self.metadata.passed_quality else '⚠️'}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Content based on channel
        if self.linkedin_post:
            lines.append("## LinkedIn Post")
            lines.append("")
            lines.append(self.linkedin_post.content)
            lines.append("")
            if self.linkedin_post.hashtags:
                lines.append("**Hashtags:** " + " ".join([f"#{tag}" for tag in self.linkedin_post.hashtags]))
            lines.append("")

        elif self.newsletter:
            lines.append("## Newsletter Email")
            lines.append("")
            lines.append(f"**Subject:** {self.newsletter.subject_line}")
            lines.append("")
            lines.append("### Body")
            lines.append("")
            lines.append(self.newsletter.body)
            lines.append("")

        elif self.blog_post:
            lines.append("## Blog Post")
            lines.append("")
            lines.append(f"### {self.blog_post.title}")
            lines.append("")
            lines.append(self.blog_post.content)
            lines.append("")

        # Metadata section
        lines.append("---")
        lines.append("")
        lines.append("## Generation Metadata")
        lines.append("")
        lines.append(f"- **Model:** {self.metadata.model_used}")
        lines.append(f"- **Final Score:** {self.metadata.final_score}/10")
        lines.append(f"- **Quality Check:** {'Passed ✅' if self.metadata.passed_quality else 'Failed ⚠️'}")
        lines.append(f"- **Refinement Iterations:** {self.metadata.refinement_iterations}")
        lines.append("")

        # Feedback
        if self.metadata.final_feedback:
            feedback = self.metadata.final_feedback

            if feedback.get('strengths'):
                lines.append("### Strengths")
                lines.append("")
                for strength in feedback['strengths']:
                    lines.append(f"- ✅ {strength}")
                lines.append("")

            if feedback.get('weaknesses'):
                lines.append("### Weaknesses")
                lines.append("")
                for weakness in feedback['weaknesses']:
                    lines.append(f"- ⚠️ {weakness}")
                lines.append("")

            if feedback.get('suggestions'):
                lines.append("### Suggestions")
                lines.append("")
                for suggestion in feedback['suggestions']:
                    lines.append(f"- 💡 {suggestion}")
                lines.append("")

        # Refinement history
        if self.metadata.refinement_history:
            lines.append("### Refinement History")
            lines.append("")
            for i, history in enumerate(self.metadata.refinement_history, 1):
                lines.append(f"**Iteration {i}:** Score {history.get('score', 0)}/10")
                lines.append("")

        return "\n".join(lines)

    def save_to_markdown(self, output_path: str) -> None:
        """Save to Markdown file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_markdown())


# Gemini structured output schemas
# These enforce the structure at the API level - the model CANNOT output invalid JSON

LINKEDIN_SCHEMA = genai.protos.Schema(
    type=genai.protos.Type.OBJECT,
    properties={
        'content': genai.protos.Schema(
            type=genai.protos.Type.STRING,
            description='The full LinkedIn post text with line breaks'
        ),
        'hashtags': genai.protos.Schema(
            type=genai.protos.Type.ARRAY,
            items=genai.protos.Schema(type=genai.protos.Type.STRING),
            description='Array of 3-5 hashtags WITHOUT the # symbol'
        )
    },
    required=['content', 'hashtags']
)

NEWSLETTER_SCHEMA = genai.protos.Schema(
    type=genai.protos.Type.OBJECT,
    properties={
        'subject_line': genai.protos.Schema(
            type=genai.protos.Type.STRING,
            description='Compelling email subject line (50-80 characters)'
        ),
        'body': genai.protos.Schema(
            type=genai.protos.Type.STRING,
            description='The full email body text with line breaks'
        )
    },
    required=['subject_line', 'body']
)

BLOG_SCHEMA = genai.protos.Schema(
    type=genai.protos.Type.OBJECT,
    properties={
        'title': genai.protos.Schema(
            type=genai.protos.Type.STRING,
            description='SEO-friendly blog post title (50-80 characters)'
        ),
        'content': genai.protos.Schema(
            type=genai.protos.Type.STRING,
            description='The full blog post content with line breaks and markdown formatting'
        )
    },
    required=['title', 'content']
)

JUDGE_SCHEMA = genai.protos.Schema(
    type=genai.protos.Type.OBJECT,
    properties={
        'score': genai.protos.Schema(
            type=genai.protos.Type.INTEGER,
            description='Overall quality score from 0-10'
        ),
        'passes_quality': genai.protos.Schema(
            type=genai.protos.Type.BOOLEAN,
            description='Whether the content passes quality threshold (8+)'
        ),
        'feedback': genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                'strengths': genai.protos.Schema(
                    type=genai.protos.Type.ARRAY,
                    items=genai.protos.Schema(type=genai.protos.Type.STRING)
                ),
                'weaknesses': genai.protos.Schema(
                    type=genai.protos.Type.ARRAY,
                    items=genai.protos.Schema(type=genai.protos.Type.STRING)
                ),
                'suggestions': genai.protos.Schema(
                    type=genai.protos.Type.ARRAY,
                    items=genai.protos.Schema(type=genai.protos.Type.STRING)
                )
            },
            required=['strengths', 'weaknesses', 'suggestions']
        ),
        'red_flags': genai.protos.Schema(
            type=genai.protos.Type.ARRAY,
            items=genai.protos.Schema(type=genai.protos.Type.STRING),
            description='Critical issues that must be fixed'
        )
    },
    required=['score', 'passes_quality', 'feedback', 'red_flags']
)

# Channel configurations
CHANNEL_CONFIGS = {
    'linkedin': {
        'name': 'LinkedIn',
        'output_class': LinkedInPost,
        'output_schema': {
            'content': str,
            'hashtags': list
        },
        'gemini_schema': LINKEDIN_SCHEMA,
        'example_folder': 'examples/linkedin'
    },
    'newsletter': {
        'name': 'Newsletter Email',
        'output_class': NewsletterEmail,
        'output_schema': {
            'subject_line': str,
            'body': str
        },
        'gemini_schema': NEWSLETTER_SCHEMA,
        'example_folder': 'examples/newsletter'
    },
    'blog': {
        'name': 'Blog Post',
        'output_class': BlogPost,
        'output_schema': {
            'title': str,
            'content': str
        },
        'gemini_schema': BLOG_SCHEMA,
        'example_folder': 'examples/blog'
    }
}


def get_channel_config(channel: str) -> dict:
    """Get configuration for a specific channel"""
    channel = channel.lower()
    if channel not in CHANNEL_CONFIGS:
        raise ValueError(f"Unknown channel: {channel}. Available: {list(CHANNEL_CONFIGS.keys())}")
    return CHANNEL_CONFIGS[channel]


def get_gemini_schema(schema_type: str):
    """
    Get Gemini structured output schema

    Args:
        schema_type: 'linkedin', 'newsletter', 'blog', or 'judge'

    Returns:
        Gemini Schema object for structured output enforcement
    """
    schemas = {
        'linkedin': LINKEDIN_SCHEMA,
        'newsletter': NEWSLETTER_SCHEMA,
        'blog': BLOG_SCHEMA,
        'judge': JUDGE_SCHEMA,
    }

    if schema_type not in schemas:
        raise ValueError(f"Unknown schema type: {schema_type}. Available: {list(schemas.keys())}")

    return schemas[schema_type]


def validate_output_schema(channel: str, output_data: dict) -> bool:
    """Validate output data against channel schema"""
    config = get_channel_config(channel)
    schema = config['output_schema']

    # Reject unexpected fields to keep outputs predictable
    unexpected = set(output_data.keys()) - set(schema.keys())
    if unexpected:
        raise ValueError(f"Unexpected field(s) for {channel} output: {', '.join(sorted(unexpected))}")

    for field_name, field_type in schema.items():
        if field_name not in output_data:
            raise ValueError(f"Missing required field '{field_name}' for {channel} output")

        actual_value = output_data[field_name]
        if not isinstance(actual_value, field_type):
            raise TypeError(
                f"Field '{field_name}' should be {field_type.__name__}, "
                f"got {type(actual_value).__name__}"
            )

        # Element-level checks for list fields
        if field_type is list and field_name == 'hashtags':
            if not all(isinstance(tag, str) for tag in actual_value):
                raise TypeError("All hashtags must be strings")

    return True

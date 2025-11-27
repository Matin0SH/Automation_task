"""
Multi-Agent Content Generation System

Unified agent that dynamically generates marketing content
across different channels (LinkedIn, Newsletter, Blog).

Uses Generator → Judge → Refiner pattern for quality control.
"""

from .content_agent import ContentAgent
from .output_schema import GeneratedContent, LinkedInPost, NewsletterEmail, BlogPost

__all__ = ['ContentAgent', 'GeneratedContent', 'LinkedInPost', 'NewsletterEmail', 'BlogPost']
__version__ = '2.0.0'

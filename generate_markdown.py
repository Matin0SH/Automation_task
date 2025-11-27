"""
Quick script to generate markdown files from existing JSON outputs
"""
import json
import sys
from pathlib import Path
from agents.output_schema import GeneratedContent, LinkedInPost, NewsletterEmail, BlogPost, GenerationMetadata

def convert_json_to_markdown(json_path):
    """Convert a JSON output file to Markdown"""
    json_path = Path(json_path)

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Reconstruct GeneratedContent object
    linkedin_post = None
    newsletter = None
    blog_post = None

    if 'linkedin_post' in data:
        linkedin_post = LinkedInPost(**data['linkedin_post'])
    if 'newsletter' in data:
        newsletter = NewsletterEmail(**data['newsletter'])
    if 'blog_post' in data:
        blog_post = BlogPost(**data['blog_post'])

    content = GeneratedContent(
        topic=data['topic'],
        channel=data['channel'],
        linkedin_post=linkedin_post,
        newsletter=newsletter,
        blog_post=blog_post,
        metadata=GenerationMetadata(**data['metadata'])
    )

    # Save markdown
    markdown_path = json_path.with_suffix('.md')
    content.save_to_markdown(str(markdown_path))

    return markdown_path

if __name__ == "__main__":
    # Convert all JSON files in output directory
    output_dir = Path("output")

    for json_file in output_dir.rglob("*.json"):
        if json_file.name == "parsed_documents.json":
            continue

        try:
            md_path = convert_json_to_markdown(json_file)
            print(f"[OK] Created: {md_path}")
        except Exception as e:
            print(f"[ERROR] Failed {json_file}: {e}")

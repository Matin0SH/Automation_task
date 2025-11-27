"""
Unified Content Generation Agent

Single agent that works across all channels (LinkedIn, Newsletter, Blog)
by dynamically loading channel-specific prompts and schemas.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

from .output_schema import (
    GeneratedContent,
    LinkedInPost,
    NewsletterEmail,
    BlogPost,
    GenerationMetadata,
    get_channel_config,
    validate_output_schema,
    get_gemini_schema
)

# Setup logging
logger = logging.getLogger(__name__)


class ContentAgent:
    """Unified agent for generating content across multiple channels"""

    def __init__(self, channel: str, max_refinement_iterations: int = 2,
                 api_config: dict = None):
        """
        Initialize Content Agent

        Args:
            channel: Channel to generate for ('linkedin', 'newsletter', 'blog')
            max_refinement_iterations: Maximum number of refinement loops
            api_config: Optional API configuration dict
        """
        # Validate channel
        self.channel = channel.lower()
        self.channel_config = get_channel_config(self.channel)

        # Load environment variables
        load_dotenv()

        # Configure Google Gemini API
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        genai.configure(api_key=api_key)

        # API configuration
        if api_config is None:
            api_config = {}

        self.model_name = api_config.get('model', 'gemini-2.5-flash')
        self.temperature = api_config.get('temperature', 0.7)
        self.max_output_tokens = api_config.get('max_output_tokens', 64000)
        self.max_retries = api_config.get('max_retries', 3)
        self.retry_delay = api_config.get('retry_delay', 2)

        # Initialize Gemini model
        self.model = genai.GenerativeModel(self.model_name)

        # Configuration
        self.max_refinement_iterations = max_refinement_iterations

        # Load prompts
        self.agents_dir = Path(__file__).parent
        self.base_prompt = self._load_prompt('base_prompt.txt')
        self.generator_prompt = self._load_prompt(f'{self.channel}/generator_prompt.txt')
        self.judge_prompt = self._load_prompt(f'{self.channel}/judge_prompt.txt')
        self.refiner_prompt = self._load_prompt(f'{self.channel}/refiner_prompt.txt')

        # Load examples
        self.examples = self._load_examples()

        logger.info(f"ContentAgent initialized for channel: {self.channel_config['name']}")
        logger.info(f"Loaded {len(self.examples)} example(s)")
        print(f"[INIT] ContentAgent initialized for channel: {self.channel_config['name']}")
        print(f"[INIT] Loaded {len(self.examples)} example(s)")

    def _sanitize_output(self, data: Dict) -> Dict:
        """
        Keep only schema fields and coerce minor type issues
        to satisfy strict validation.
        """
        cleaned = {}

        if self.channel == 'linkedin':
            cleaned['content'] = data.get('content', '')
            hashtags = data.get('hashtags', [])
            if isinstance(hashtags, list):
                hashtags = [str(tag) for tag in hashtags if isinstance(tag, (str, int, float))]
            else:
                hashtags = []
            cleaned['hashtags'] = hashtags
        elif self.channel == 'newsletter':
            cleaned['subject_line'] = data.get('subject_line', '')
            cleaned['body'] = data.get('body', '')
        elif self.channel == 'blog':
            cleaned['title'] = data.get('title', '')
            cleaned['content'] = data.get('content', '')

        return cleaned

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from file"""
        prompt_path = self.agents_dir / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_examples(self) -> List[Dict]:
        """Load all examples for this channel from examples folder"""
        examples = []
        examples_dir = Path(self.channel_config['example_folder'])

        if not examples_dir.exists():
            print(f"[WARN] Examples directory not found: {examples_dir}")
            return examples

        for example_file in examples_dir.glob('*.json'):
            try:
                with open(example_file, 'r', encoding='utf-8') as f:
                    example_data = json.load(f)
                    examples.append(example_data)
                    print(f"[OK] Loaded example: {example_file.name}")
            except Exception as e:
                print(f"[WARN] Failed to load example {example_file}: {str(e)}")

        return examples

    def _format_examples(self) -> str:
        """Format examples for inclusion in prompt"""
        if not self.examples:
            return "No examples available."

        formatted = []
        for i, example in enumerate(self.examples, 1):
            formatted.append(f"### Example {i}: {example.get('topic', 'Unknown Topic')}")

            # Format based on channel
            if self.channel == 'linkedin':
                formatted.append(f"```\n{example.get('content', '')}\n```")
                formatted.append(f"Hashtags: {', '.join(['#' + h for h in example.get('hashtags', [])])}")
            elif self.channel == 'newsletter':
                formatted.append(f"Subject: {example.get('subject_line', '')}")
                formatted.append(f"```\n{example.get('body', '')}\n```")
            elif self.channel == 'blog':
                formatted.append(f"Title: {example.get('title', '')}")
                formatted.append(f"```\n{example.get('content', '')}\n```")

            formatted.append("")

        return "\n".join(formatted)

    def _format_documents(self, documents: Dict[str, str]) -> str:
        """Format source documents for prompt"""
        doc_order = [
            ('product_roadmap', 'Product Roadmap Summary'),
            ('engineering_ticket', 'Engineering Ticket'),
            ('meeting_transcript', 'Meeting Transcript'),
            ('marketing_notes', 'Marketing & Product Meeting Notes'),
            ('customer_feedback', 'Customer Feedback Snippets')
        ]

        formatted = []
        for key, title in doc_order:
            content = documents.get(key, 'Not available')
            if content and content != 'Not available':
                formatted.append(f"## {title}\n\n{content}\n")

        return "\n".join(formatted)

    def _call_gemini(self, prompt: str, schema_type: str = None) -> str:
        """
        Call Google Gemini API with retry logic and structured output

        Args:
            prompt: The prompt to send
            schema_type: Schema to enforce ('linkedin', 'newsletter', 'blog', 'judge')
                        If None, uses basic JSON mode without schema enforcement

        Returns:
            JSON string response from Gemini
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Gemini API call attempt {attempt + 1}/{self.max_retries}")

                # Build generation config
                gen_config = {
                    'temperature': self.temperature,
                    'max_output_tokens': self.max_output_tokens,
                    'response_mime_type': "application/json",
                }

                # Add structured schema if specified
                if schema_type:
                    schema = get_gemini_schema(schema_type)
                    gen_config['response_schema'] = schema
                    logger.debug(f"Using structured output schema: {schema_type}")

                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(**gen_config)
                )
                return response.text
            except Exception as e:
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("All retry attempts exhausted")
                    raise Exception(f"Gemini API call failed after {self.max_retries} attempts: {str(e)}")

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response with smart quote handling and encoding fixes"""
        response = response.strip()

        # Remove markdown code blocks
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()

        # Fix encoding issues (replace invalid UTF-8 sequences)
        # The � character indicates encoding problems
        response = response.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')

        # Replace smart/curly quotes and other typographic characters
        # These often appear in LLM responses and break JSON parsing
        replacements = {
            '"': '"',   # Left double quotation mark
            '"': '"',   # Right double quotation mark
            ''': "'",   # Left single quotation mark
            ''': "'",   # Right single quotation mark
            '—': '-',   # Em dash
            '–': '-',   # En dash
            '…': '...', # Horizontal ellipsis
            '`': "'",   # Backtick to straight quote
        }

        for smart, straight in replacements.items():
            response = response.replace(smart, straight)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}\nResponse: {response}")

    def generate(self, topic: str, documents: Dict[str, str]) -> Dict:
        """
        Generate content for the configured channel

        Args:
            topic: Topic name
            documents: Dictionary containing source documents

        Returns:
            Dictionary with channel-specific content
        """
        print(f"\n[Generator] Generating {self.channel} content for topic: {topic}")

        # Build full prompt
        examples_text = self._format_examples()
        documents_text = self._format_documents(documents)

        full_prompt = f"""{self.base_prompt}

## TOPIC
{topic}

## SOURCE DOCUMENTS
{documents_text}

{self.generator_prompt}
""".replace('{EXAMPLES_PLACEHOLDER}', examples_text)

        # Call Gemini with structured output schema enforcement
        # The schema GUARANTEES valid JSON output matching our structure
        response = self._call_gemini(full_prompt, schema_type=self.channel)

        # Parse response (should always be valid JSON now thanks to schema)
        result = self._parse_json_response(response)

        # Remove unexpected fields / coerce types before validation
        result = self._sanitize_output(result)

        # Validate against schema
        validate_output_schema(self.channel, result)

        print(f"[Generator] Successfully generated content")
        return result

    def judge(self, content_data: Dict) -> Dict:
        """
        Evaluate content quality

        Args:
            content_data: The generated content

        Returns:
            Dictionary with evaluation results
        """
        print(f"\n[Judge] Evaluating {self.channel} content...")

        # Format content for judging based on channel
        if self.channel == 'linkedin':
            formatted_content = f"{content_data['content']}\n\n" + " ".join([f"#{tag}" for tag in content_data['hashtags']])
        elif self.channel == 'newsletter':
            formatted_content = f"Subject: {content_data['subject_line']}\n\n{content_data['body']}"
        elif self.channel == 'blog':
            formatted_content = f"Title: {content_data['title']}\n\n{content_data['content']}"

        # Build judge prompt
        judge_prompt_filled = self.judge_prompt.replace(
            '{POST_CONTENT_PLACEHOLDER}',
            formatted_content
        )

        full_prompt = f"""{self.base_prompt}

{judge_prompt_filled}
"""

        # Call Gemini with judge schema enforcement
        response = self._call_gemini(full_prompt, schema_type='judge')

        # Parse response (schema ensures valid structure)
        result = self._parse_json_response(response)

        score = result.get('score', 0)
        passes = result.get('passes_quality', False)
        status = "PASS" if passes else "FAIL"

        print(f"[Judge] Score: {score}/10 | Status: {status}")

        return result

    def refine(self, original_content: Dict, judge_result: Dict) -> Dict:
        """
        Refine content based on judge feedback

        Args:
            original_content: Original content output
            judge_result: Judge evaluation results

        Returns:
            Dictionary with refined content
        """
        print(f"\n[Refiner] Refining {self.channel} content based on feedback...")

        # Format original content
        if self.channel == 'linkedin':
            original_text = original_content['content']
        elif self.channel == 'newsletter':
            original_text = f"Subject: {original_content['subject_line']}\n\n{original_content['body']}"
        elif self.channel == 'blog':
            original_text = f"Title: {original_content['title']}\n\n{original_content['content']}"

        # Format judge results
        criteria_scores = json.dumps(judge_result.get('criteria_scores', {}), indent=2)
        strengths = "\n".join([f"- {s}" for s in judge_result.get('feedback', {}).get('strengths', [])])
        weaknesses = "\n".join([f"- {w}" for w in judge_result.get('feedback', {}).get('weaknesses', [])])
        suggestions = "\n".join([f"- {s}" for s in judge_result.get('feedback', {}).get('suggestions', [])])
        red_flags = "\n".join([f"- {r}" for r in judge_result.get('red_flags', [])]) or "None"

        # Build refiner prompt
        refiner_prompt_filled = self.refiner_prompt
        refiner_prompt_filled = refiner_prompt_filled.replace('{ORIGINAL_POST_PLACEHOLDER}', original_text)
        refiner_prompt_filled = refiner_prompt_filled.replace('{SCORE}', str(judge_result.get('score', 0)))
        refiner_prompt_filled = refiner_prompt_filled.replace('{PASS_FAIL}', 'FAIL')
        refiner_prompt_filled = refiner_prompt_filled.replace('{CRITERIA_SCORES_PLACEHOLDER}', criteria_scores)
        refiner_prompt_filled = refiner_prompt_filled.replace('{STRENGTHS_PLACEHOLDER}', strengths)
        refiner_prompt_filled = refiner_prompt_filled.replace('{WEAKNESSES_PLACEHOLDER}', weaknesses)
        refiner_prompt_filled = refiner_prompt_filled.replace('{SUGGESTIONS_PLACEHOLDER}', suggestions)
        refiner_prompt_filled = refiner_prompt_filled.replace('{RED_FLAGS_PLACEHOLDER}', red_flags)

        full_prompt = f"""{self.base_prompt}

{refiner_prompt_filled}
"""

        # Call Gemini with channel schema enforcement
        response = self._call_gemini(full_prompt, schema_type=self.channel)

        # Parse response (schema ensures valid structure)
        result = self._parse_json_response(response)

        # Remove unexpected fields / coerce types before validation
        result = self._sanitize_output(result)

        # Validate against schema
        validate_output_schema(self.channel, result)

        changes = result.get('changes_made', [])
        if changes:
            print(f"[Refiner] Made {len(changes)} improvements")
            for change in changes:
                print(f"  - {change}")

        return result

    def generate_with_quality_control(self, topic: str, documents: Dict[str, str]) -> GeneratedContent:
        """
        Generate content with automatic quality control loop

        Args:
            topic: Topic name
            documents: Dictionary containing source documents

        Returns:
            GeneratedContent object with metadata
        """
        print("=" * 80)
        print(f"ContentAgent [{self.channel_config['name']}]: Starting generation for '{topic}'")
        print("=" * 80)

        # Step 1: Initial generation
        current_content = self.generate(topic, documents)

        iteration = 0
        refinement_history = []

        # Step 2: Quality control loop
        while iteration < self.max_refinement_iterations:
            # Judge the content
            judge_result = self.judge(current_content)

            # Check if it passes
            if judge_result.get('passes_quality', False):
                print(f"\n[SUCCESS] Content passed quality check on iteration {iteration + 1}")
                break

            # If failed and we have iterations left, refine
            if iteration < self.max_refinement_iterations - 1:
                print(f"\n[Refining] Attempt {iteration + 1}/{self.max_refinement_iterations}")

                # Store refinement history
                refinement_history.append({
                    'iteration': iteration + 1,
                    'score': judge_result.get('score', 0),
                    'feedback': judge_result.get('feedback', {})
                })

                # Refine the content
                current_content = self.refine(current_content, judge_result)
                iteration += 1
            else:
                print(f"\n[WARNING] Max refinement iterations reached. Using best available version.")
                break

        # Final result
        final_judge_result = self.judge(current_content)

        # Build output object based on channel
        output = GeneratedContent(
            topic=topic,
            channel=self.channel,
            metadata=GenerationMetadata(
                channel=self.channel,
                final_score=final_judge_result.get('score', 0),
                passed_quality=final_judge_result.get('passes_quality', False),
                refinement_iterations=iteration,
                refinement_history=refinement_history,
                final_feedback=final_judge_result.get('feedback', {}),
                model_used=self.model_name
            )
        )

        # Set channel-specific content
        if self.channel == 'linkedin':
            output.linkedin_post = LinkedInPost(
                content=current_content['content'],
                hashtags=current_content['hashtags']
            )
        elif self.channel == 'newsletter':
            output.newsletter = NewsletterEmail(
                subject_line=current_content['subject_line'],
                body=current_content['body']
            )
        elif self.channel == 'blog':
            output.blog_post = BlogPost(
                title=current_content['title'],
                content=current_content['content']
            )

        print("\n" + "=" * 80)
        print(f"FINAL RESULT: Score {output.metadata.final_score}/10")
        print("=" * 80)

        return output

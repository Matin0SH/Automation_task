"""
Main Workflow Script

Complete pipeline:
1. Parse topic documents from source folder
2. Generate content for specified channel(s) using unified agent
3. Save outputs with metadata

Dynamic: Works for any channel (linkedin, newsletter, blog)
Supports: --all channels, --all-topics, topic selection
"""

import sys
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tool import TopicParser
from agents import ContentAgent
from config_loader import load_config


def setup_logging(config):
    """Setup logging configuration"""
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers = []

    # File handler
    handlers.append(logging.FileHandler(config.log_file, encoding='utf-8'))

    # Console handler
    if config.log_console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=config.log_format,
        handlers=handlers
    )

    return logging.getLogger(__name__)


def generate_channel_content(channel, topic_data, config, logger, topic_output_dir):
    """
    Worker function for parallel channel processing

    Generates content for a single channel using the ContentAgent.
    This function is designed to be called in parallel via ThreadPoolExecutor.

    Args:
        channel: Channel name (linkedin, newsletter, blog)
        topic_data: Parsed topic data
        config: Configuration object
        logger: Logger instance
        topic_output_dir: Path to topic output directory

    Returns:
        Dictionary with generation results
    """
    try:
        logger.info(f"Starting {channel} content generation")
        print(f"\n{'='*80}")
        print(f"Generating {channel.upper()} content...")
        print(f"{'='*80}")

        # Initialize agent with config
        api_config = {
            'model': config.api_model,
            'temperature': config.api_temperature,
            'max_output_tokens': config.api_max_tokens,
            'max_retries': config.api_max_retries,
            'retry_delay': config.api_retry_delay
        }

        agent = ContentAgent(
            channel=channel,
            max_refinement_iterations=config.max_refinement_iterations,
            api_config=api_config
        )

        # Generate content (I/O-bound: API calls to Gemini)
        result = agent.generate_with_quality_control(
            topic=topic_data.topic,
            documents={
                'product_roadmap': topic_data.documents.product_roadmap,
                'engineering_ticket': topic_data.documents.engineering_ticket,
                'meeting_transcript': topic_data.documents.meeting_transcript,
                'marketing_notes': topic_data.documents.marketing_notes,
                'customer_feedback': topic_data.documents.customer_feedback
            }
        )

        # Save channel output (both JSON and Markdown)
        content_output_file = topic_output_dir / f"{channel}.json"
        content_markdown_file = topic_output_dir / f"{channel}.md"

        result.save_to_file(str(content_output_file))
        result.save_to_markdown(str(content_markdown_file))

        logger.info(f"Saved {channel} content: {content_output_file}")
        logger.info(f"Saved {channel} markdown: {content_markdown_file}")

        return {
            'channel': channel,
            'success': True,
            'score': result.metadata.final_score,
            'file': str(content_output_file),
            'markdown': str(content_markdown_file)
        }

    except Exception as e:
        logger.error(f"Failed to generate {channel} content: {str(e)}", exc_info=True)
        return {
            'channel': channel,
            'success': False,
            'error': str(e)
        }


def process_topic(topic_name, topic_data, channels, config, logger):
    """
    Process a single topic for one or more channels (in parallel)

    Uses ThreadPoolExecutor to generate content for multiple channels
    concurrently, significantly reducing total processing time for
    multi-channel workflows.

    Args:
        topic_name: Name of the topic
        topic_data: Parsed topic data
        channels: List of channels to generate for
        config: Configuration object
        logger: Logger instance

    Returns:
        Dictionary of results per channel
    """
    results = {}

    # Create topic output directory
    topic_output_dir = Path(config.output_dir) / topic_name
    topic_output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {topic_output_dir}")

    # Save parsed documents first (checkpoint)
    topic_output_file = topic_output_dir / "parsed_documents.json"
    try:
        with open(topic_output_file, 'w', encoding='utf-8') as f:
            f.write(topic_data.to_json())
        logger.info(f"Saved parsed documents: {topic_output_file}")
        print(f"[OK] Parsed documents saved")
    except Exception as e:
        logger.error(f"Failed to save parsed documents: {str(e)}")

    # Process channels in parallel using ThreadPoolExecutor
    # This is optimal for I/O-bound tasks (API calls to Gemini)
    print(f"\n[INFO] Processing {len(channels)} channel(s) in parallel...")

    with ThreadPoolExecutor(max_workers=len(channels)) as executor:
        # Submit all channel generation tasks
        future_to_channel = {
            executor.submit(generate_channel_content, channel, topic_data, config, logger, topic_output_dir): channel
            for channel in channels
        }

        # Collect results as they complete (best UX)
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                # Get result from worker
                channel_result = future.result()
                results[channel_result['channel']] = channel_result

                # Display result
                if channel_result['success']:
                    print(f"[OK] {channel.capitalize()} content saved:")
                    print(f"     JSON: {channel_result['file']}")
                    print(f"     Markdown: {channel_result['markdown']}")
                else:
                    print(f"[ERROR] Failed to generate {channel} content: {channel_result['error']}")

            except Exception as e:
                logger.error(f"Exception in {channel} generation future: {str(e)}")
                results[channel] = {
                    'success': False,
                    'error': str(e)
                }

    return results


def main():
    """Main workflow with argument parsing"""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Multi-Channel Marketing Content Generation'
    )
    parser.add_argument(
        'channel',
        nargs='?',
        default=None,
        help='Channel to generate for (linkedin, newsletter, blog)'
    )
    parser.add_argument(
        '--all-channels',
        action='store_true',
        help='Generate content for all enabled channels'
    )
    parser.add_argument(
        '--all-topics',
        action='store_true',
        help='Process all topics in source directory'
    )
    parser.add_argument(
        '--topic',
        help='Specific topic to process (by name or index)'
    )
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to config file'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"[ERROR] Configuration file not found: {args.config}")
        print("Creating default config.json...")
        # Config will be created by load_config with defaults
        return 1

    # Setup logging
    logger = setup_logging(config)
    logger.info("="*80)
    logger.info("WORKFLOW STARTED")
    logger.info("="*80)

    print("=" * 80)
    print("MULTI-CHANNEL MARKETING CONTENT GENERATION WORKFLOW")
    print("=" * 80)

    # Determine channels to process
    if args.all_channels or config.generate_all_channels:
        channels = config.enabled_channels
        print(f"Channels: ALL ({', '.join([c.upper() for c in channels])})")
    elif args.channel:
        channels = [args.channel.lower()]
        print(f"Channel: {args.channel.upper()}")
    else:
        channels = [config.default_channel]
        print(f"Channel: {config.default_channel.upper()} (default)")

    print("=" * 80)

    # Parse topics
    print(f"\n[STEP 1] Parsing topics from source folder...")
    print("-" * 80)

    try:
        topic_parser = TopicParser(source_dir=config.source_dir, output_dir=config.output_dir)
        all_topics = topic_parser.list_topics()
    except Exception as e:
        logger.error(f"Failed to initialize parser: {str(e)}")
        print(f"[ERROR] Failed to initialize parser: {str(e)}")
        return 1

    if not all_topics:
        logger.error("No topics found in source directory")
        print(f"[ERROR] No topics found in {config.source_dir}/")
        return 1

    print(f"Found {len(all_topics)} topic(s):")
    for i, topic in enumerate(all_topics, 1):
        print(f"  {i}. {topic}")

    # Determine which topics to process
    topics_to_process = []

    if args.all_topics or config.process_all_topics:
        topics_to_process = all_topics
        print(f"\nProcessing ALL {len(topics_to_process)} topic(s)")
    elif args.topic:
        # Try to match by index or name
        if args.topic.isdigit():
            idx = int(args.topic) - 1
            if 0 <= idx < len(all_topics):
                topics_to_process = [all_topics[idx]]
            else:
                print(f"[ERROR] Invalid topic index: {args.topic}")
                return 1
        else:
            # Match by name
            matching = [t for t in all_topics if args.topic.lower() in t.lower()]
            if matching:
                topics_to_process = matching
            else:
                print(f"[ERROR] No topic found matching: {args.topic}")
                return 1
    else:
        # Default: process first topic
        topics_to_process = [all_topics[0]]

    print(f"Selected {len(topics_to_process)} topic(s) to process\n")

    # Process each topic
    all_results = {}

    for topic_idx, topic_name in enumerate(topics_to_process, 1):
        print(f"\n{'#'*80}")
        print(f"TOPIC {topic_idx}/{len(topics_to_process)}: {topic_name}")
        print(f"{'#'*80}")

        logger.info(f"Processing topic: {topic_name}")

        # Parse topic documents
        try:
            print("\n[INFO] Extracting documents...")
            topic_data = topic_parser.parse_topic(topic_name, save_output=False)
            logger.info(f"Parsed {topic_data.metadata.file_count} documents")
            print(f"[OK] Parsed {topic_data.metadata.file_count} documents")

            if topic_data.metadata.missing_documents:
                logger.warning(f"Missing documents: {topic_data.metadata.missing_documents}")
                print(f"[WARN] Missing: {', '.join(topic_data.metadata.missing_documents)}")

        except Exception as e:
            logger.error(f"Failed to parse topic {topic_name}: {str(e)}", exc_info=True)
            print(f"[ERROR] Failed to parse topic: {str(e)}")
            all_results[topic_name] = {'error': str(e)}
            continue

        # Process topic for all channels
        topic_results = process_topic(topic_name, topic_data, channels, config, logger)
        all_results[topic_name] = topic_results

    # Final summary
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)

    total_success = 0
    total_failed = 0

    for topic_name, topic_results in all_results.items():
        print(f"\nTopic: {topic_name}")
        if 'error' in topic_results:
            print(f"  [FAILED] {topic_results['error']}")
            total_failed += 1
        else:
            for channel, result in topic_results.items():
                if result['success']:
                    print(f"  [{channel.upper()}] Score: {result['score']}/10 - {result['file']}")
                    total_success += 1
                else:
                    print(f"  [{channel.upper()}] FAILED: {result['error']}")
                    total_failed += 1

    print("\n" + "=" * 80)
    print(f"Total Successful: {total_success}")
    print(f"Total Failed: {total_failed}")
    print("=" * 80)

    logger.info(f"Workflow completed - Success: {total_success}, Failed: {total_failed}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INFO] Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

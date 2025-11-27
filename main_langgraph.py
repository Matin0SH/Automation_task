"""
LangGraph-based Multi-Channel Marketing Content Generation Workflow

Clean implementation with proper state separation to avoid concurrent update errors.

Usage:
    python main_langgraph.py --all-channels
    python main_langgraph.py --topic "Document Compare" --all-channels
    python main_langgraph.py --channel linkedin
    python main_langgraph.py --checkpoint --thread-id my_workflow_123
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Import LangGraph components
from langgraph.checkpoint.memory import MemorySaver

# Import workflow components
from langgraph_workflow.state import create_initial_workflow_state
from langgraph_workflow.graphs import create_main_graph, create_main_graph_with_checkpointing

# Import existing modules
from config_loader import load_config
from tool import TopicParser


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


def main():
    """Main workflow with LangGraph orchestration"""

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Multi-Channel Marketing Content Generation (LangGraph)'
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
    parser.add_argument(
        '--checkpoint',
        action='store_true',
        help='Enable checkpointing (allows resume)'
    )
    parser.add_argument(
        '--thread-id',
        help='Thread ID for checkpointing (auto-generated if not provided)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"[ERROR] Configuration file not found: {args.config}")
        return 1

    # Setup logging
    logger = setup_logging(config)
    logger.info("="*80)
    logger.info("LANGGRAPH WORKFLOW STARTED")
    logger.info("="*80)

    print("=" * 80)
    print("MULTI-CHANNEL MARKETING CONTENT GENERATION (LangGraph)")
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

    # Create graph (with or without checkpointing)
    print(f"\n[STEP 2] Initializing LangGraph workflow...")
    print("-" * 80)

    if args.checkpoint:
        checkpointer = MemorySaver()
        graph = create_main_graph_with_checkpointing(checkpointer)
        print("[OK] Checkpointing ENABLED (MemorySaver)")
    else:
        graph = create_main_graph()
        checkpointer = None
        print("[OK] Checkpointing DISABLED")

    # Process each topic
    all_results = {}

    for topic_idx, topic_name in enumerate(topics_to_process, 1):
        print(f"\n{'#'*80}")
        print(f"TOPIC {topic_idx}/{len(topics_to_process)}: {topic_name}")
        print(f"{'#'*80}")

        logger.info(f"Processing topic: {topic_name}")

        # Generate thread ID
        if args.thread_id:
            thread_id = args.thread_id
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            thread_id = f"{topic_name}_{timestamp}"

        # Create initial state
        initial_state = create_initial_workflow_state(
            topic=topic_name,
            channels=channels,
            config={
                'source_dir': config.source_dir,
                'output_dir': config.output_dir,
                'max_refinement_iterations': config.max_refinement_iterations,
                'quality_threshold': 8.0,
                'api_model': config.api_model,
                'api_temperature': config.api_temperature,
                'api_max_tokens': config.api_max_tokens,
                'api_max_retries': config.api_max_retries,
                'api_retry_delay': config.api_retry_delay,
            }
        )

        # Config for graph execution
        graph_config = {
            "configurable": {
                "thread_id": thread_id
            }
        } if args.checkpoint else None

        try:
            # Execute graph
            print(f"\n[INFO] Executing LangGraph workflow...")
            print(f"[INFO] Thread ID: {thread_id}")
            print("-" * 80)

            # Invoke graph (simple execution)
            result = graph.invoke(initial_state, graph_config)

            # Display results
            print(f"\n{'='*80}")
            print("WORKFLOW RESULTS")
            print(f"{'='*80}")

            if result.get('status') == 'completed':
                print(f"[SUCCESS] Workflow completed")
                print(f"\nChannel Results:")

                for channel, channel_result in result.get('channel_results', {}).items():
                    score = channel_result.get('final_score', 0)
                    passed = channel_result.get('passed_quality', False)
                    iterations = channel_result.get('refinement_iterations', 0)
                    time_taken = channel_result.get('generation_time', 0)

                    status_icon = "[PASS]" if passed else "[FAIL]"
                    print(f"\n  [{channel.upper()}] {status_icon}")
                    print(f"    Score: {score}/10")
                    print(f"    Iterations: {iterations}")
                    print(f"    Time: {time_taken:.1f}s")

                # Summary metrics
                print(f"\nSummary:")
                print(f"  Total Tokens: {result.get('total_tokens_used', 0):,}")
                print(f"  Total API Calls: {result.get('total_api_calls', 0)}")
                print(f"  Estimated Cost: ${result.get('total_cost', 0):.4f}")

                all_results[topic_name] = result

            else:
                print(f"[ERROR] Workflow failed or incomplete")
                errors = result.get('errors', [])
                if errors:
                    print(f"\nErrors ({len(errors)}):")
                    for error in errors:
                        print(f"  - [{error.get('node', 'unknown')}] {error.get('error', 'Unknown error')}")

                all_results[topic_name] = {'error': 'Workflow failed'}

        except Exception as e:
            logger.error(f"Failed to process topic {topic_name}: {str(e)}", exc_info=True)
            print(f"[ERROR] Failed to process topic: {str(e)}")
            all_results[topic_name] = {'error': str(e)}
            continue

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    total_success = sum(
        1 for result in all_results.values()
        if result.get('status') == 'completed'
    )
    total_failed = len(all_results) - total_success

    print(f"Total Topics Processed: {len(all_results)}")
    print(f"Successful: {total_success}")
    print(f"Failed: {total_failed}")
    print("=" * 80)

    logger.info(f"LangGraph workflow completed - Success: {total_success}, Failed: {total_failed}")

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

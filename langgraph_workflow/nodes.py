"""
Node Implementations for LangGraph Workflow

All nodes updated to use the new state schemas with no overlapping keys.
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Import existing modules
from tool import TopicParser
from agents import ContentAgent
from agents.output_schema import GeneratedContent, LinkedInPost, NewsletterEmail, BlogPost, GenerationMetadata

# Import state schemas
from .state import WorkflowState, ChannelState, ChannelResult

logger = logging.getLogger(__name__)


# ============================================================================
# MAIN WORKFLOW NODES
# ============================================================================

def parse_documents_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Node: Parse documents from source folder

    Args:
        state: Current workflow state

    Returns:
        Updated state with parsed_documents populated
    """
    logger.info("=== PARSE DOCUMENTS NODE ===")
    logger.info(f"Topic: {state['topic']}")

    try:
        config = state['config']
        topic = state['topic']

        # Initialize parser
        parser = TopicParser(
            source_dir=config.get('source_dir', 'source'),
            output_dir=config.get('output_dir', 'output')
        )

        # Parse topic documents
        topic_data = parser.parse_topic(topic, save_output=False)

        logger.info(f"Parsed {topic_data.metadata.file_count} documents")

        # Convert to dictionary for state storage
        parsed_docs_dict = {
            'topic': topic_data.topic,
            'documents': {
                'product_roadmap': topic_data.documents.product_roadmap,
                'engineering_ticket': topic_data.documents.engineering_ticket,
                'meeting_transcript': topic_data.documents.meeting_transcript,
                'marketing_notes': topic_data.documents.marketing_notes,
                'customer_feedback': topic_data.documents.customer_feedback,
            },
            'metadata': {
                'topic_folder': topic_data.metadata.topic_folder,
                'file_count': topic_data.metadata.file_count,
                'missing_documents': topic_data.metadata.missing_documents,
            }
        }

        return {
            "parsed_documents": parsed_docs_dict,
            "current_phase": "generating",
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Failed to parse documents: {str(e)}", exc_info=True)
        error_record = {
            "node": "parse_documents",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "errors": [error_record],
            "status": "failed",
            "current_phase": "error"
        }


def aggregate_results_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Node: Aggregate results from all channel subgraphs

    This node collects the final states from parallel channel subgraphs
    and builds ChannelResult objects for storage in WorkflowState.

    Args:
        state: Current workflow state with channel_results populated

    Returns:
        Updated state with aggregated metrics
    """
    logger.info("=== AGGREGATE RESULTS NODE ===")

    try:
        channel_results = state.get('channel_results', {})

        if not channel_results:
            logger.warning("No channel results to aggregate")
            return {"current_phase": "saving"}

        # Calculate totals
        total_tokens = sum(
            result.get('tokens_used', 0)
            for result in channel_results.values()
        )

        total_api_calls = sum(
            result.get('api_calls', 0)
            for result in channel_results.values()
        )

        # Calculate cost (Gemini 2.5 Flash pricing)
        # $0.075 per 1M input tokens, $0.30 per 1M output tokens
        # Assuming 70% input, 30% output
        input_tokens = int(total_tokens * 0.7)
        output_tokens = int(total_tokens * 0.3)
        total_cost = (input_tokens / 1_000_000 * 0.075) + (output_tokens / 1_000_000 * 0.30)

        # Calculate average score
        scores = [
            result.get('final_score', 0)
            for result in channel_results.values()
        ]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Calculate success rate
        passed_count = sum(
            1 for result in channel_results.values()
            if result.get('passed_quality', False)
        )
        success_rate = passed_count / len(channel_results) if channel_results else 0

        logger.info(f"Total tokens: {total_tokens}")
        logger.info(f"Total API calls: {total_api_calls}")
        logger.info(f"Estimated cost: ${total_cost:.4f}")
        logger.info(f"Average score: {avg_score:.1f}/10")
        logger.info(f"Success rate: {success_rate:.1%}")

        return {
            "total_tokens_used": total_tokens,
            "total_api_calls": total_api_calls,
            "total_cost": total_cost,
            "current_phase": "saving",
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Failed to aggregate results: {str(e)}", exc_info=True)
        error_record = {
            "node": "aggregate_results",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "errors": [error_record]
        }


def save_results_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Node: Save results to output directory (JSON + Markdown)

    Args:
        state: Current workflow state with channel_results

    Returns:
        Updated state with completion status
    """
    logger.info("=== SAVE RESULTS NODE ===")

    try:
        topic = state['topic']
        config = state['config']
        channel_results = state.get('channel_results', {})

        # Create output directory
        output_dir = Path(config.get('output_dir', 'output')) / topic
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save parsed documents checkpoint
        if state.get('parsed_documents'):
            parsed_docs_path = output_dir / "parsed_documents.json"
            with open(parsed_docs_path, 'w', encoding='utf-8') as f:
                json.dump(state['parsed_documents'], f, indent=2, ensure_ascii=False)
            logger.info(f"Saved parsed documents: {parsed_docs_path}")

        # Save each channel result
        for channel_name, result in channel_results.items():
            if not result.get('final_content'):
                logger.warning(f"No final content for {channel_name}, skipping save")
                continue

            # Build GeneratedContent object
            content_obj = GeneratedContent(
                topic=topic,
                channel=channel_name,
                metadata=GenerationMetadata(
                    channel=channel_name,
                    final_score=result.get('final_score', 0),
                    passed_quality=result.get('passed_quality', False),
                    refinement_iterations=result.get('refinement_iterations', 0),
                    refinement_history=result.get('refinement_history', []),
                    final_feedback=result.get('final_feedback', {}),
                    model_used=result.get('model_used', 'gemini-2.5-flash')
                )
            )

            # Set channel-specific content
            final_content = result['final_content']
            if channel_name == 'linkedin':
                content_obj.linkedin_post = LinkedInPost(
                    content=final_content.get('content', ''),
                    hashtags=final_content.get('hashtags', [])
                )
            elif channel_name == 'newsletter':
                content_obj.newsletter = NewsletterEmail(
                    subject_line=final_content.get('subject_line', ''),
                    body=final_content.get('body', '')
                )
            elif channel_name == 'blog':
                content_obj.blog_post = BlogPost(
                    title=final_content.get('title', ''),
                    content=final_content.get('content', '')
                )

            # Save JSON
            json_path = output_dir / f"{channel_name}.json"
            content_obj.save_to_file(str(json_path))
            logger.info(f"Saved {channel_name} JSON: {json_path}")

            # Save Markdown
            md_path = output_dir / f"{channel_name}.md"
            content_obj.save_to_markdown(str(md_path))
            logger.info(f"Saved {channel_name} Markdown: {md_path}")

        return {
            "end_time": datetime.now().isoformat(),
            "status": "completed",
            "current_phase": "completed"
        }

    except Exception as e:
        logger.error(f"Failed to save results: {str(e)}", exc_info=True)
        error_record = {
            "node": "save_results",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "errors": [error_record],
            "status": "failed",
            "current_phase": "error"
        }


# ============================================================================
# CHANNEL SUBGRAPH NODES
# ============================================================================

def load_context_node(state: ChannelState) -> Dict[str, Any]:
    """
    Node: Load context for channel generation

    Args:
        state: Current channel state

    Returns:
        Updated state with status
    """
    channel = state['channel_name']
    logger.info(f"=== LOAD CONTEXT NODE [{channel}] ===")

    # Context is already loaded in initial state
    # This node serves as entry point
    return {
        "internal_status": "generating"
    }


def generate_content_node(state: ChannelState) -> Dict[str, Any]:
    """
    Node: Generate initial content for channel

    Args:
        state: Current channel state

    Returns:
        Updated state with current_content populated
    """
    channel = state['channel_name']
    logger.info(f"=== GENERATE CONTENT NODE [{channel}] ===")

    try:
        # Initialize agent
        agent = ContentAgent(
            channel=channel,
            max_refinement_iterations=state['max_iterations'],
            api_config={
                'model': state['input_config'].get('api_model', 'gemini-2.5-flash'),
                'temperature': state['input_config'].get('api_temperature', 0.7),
                'max_output_tokens': state['input_config'].get('api_max_tokens', 64000),
                'max_retries': state['input_config'].get('api_max_retries', 3),
                'retry_delay': state['input_config'].get('api_retry_delay', 2),
            }
        )

        # Generate content
        content = agent.generate(
            topic=state['input_topic'],
            documents=state['input_documents']
        )

        logger.info(f"[{channel}] Content generated successfully")

        # Estimate tokens
        estimated_tokens = len(json.dumps(content)) // 4

        return {
            "current_content": content,
            "tokens_used": state.get('tokens_used', 0) + estimated_tokens,
            "api_calls": state.get('api_calls', 0) + 1,
            "internal_status": "judging"
        }

    except Exception as e:
        logger.error(f"[{channel}] Generation failed: {str(e)}", exc_info=True)
        error_record = {
            "node": "generate_content",
            "channel": channel,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "internal_errors": state.get('internal_errors', []) + [error_record],
            "internal_status": "failed"
        }


def judge_content_node(state: ChannelState) -> Dict[str, Any]:
    """
    Node: Evaluate content quality

    Args:
        state: Current channel state with current_content

    Returns:
        Updated state with judge_results appended
    """
    channel = state['channel_name']
    logger.info(f"=== JUDGE CONTENT NODE [{channel}] ===")

    try:
        # Initialize agent
        agent = ContentAgent(
            channel=channel,
            max_refinement_iterations=state['max_iterations'],
            api_config={
                'model': state['input_config'].get('api_model', 'gemini-2.5-flash'),
                'temperature': state['input_config'].get('api_temperature', 0.7),
                'max_output_tokens': state['input_config'].get('api_max_tokens', 64000),
                'max_retries': state['input_config'].get('api_max_retries', 3),
                'retry_delay': state['input_config'].get('api_retry_delay', 2),
            }
        )

        # Judge content
        judge_result = agent.judge(state['current_content'])

        logger.info(f"[{channel}] Score: {judge_result.get('score', 0)}/10")

        # Append to judge results
        judge_results = state.get('judge_results', []).copy()
        judge_results.append(judge_result)

        # Estimate tokens
        estimated_tokens = len(json.dumps(judge_result)) // 4

        return {
            "judge_results": judge_results,
            "tokens_used": state.get('tokens_used', 0) + estimated_tokens,
            "api_calls": state.get('api_calls', 0) + 1,
            "internal_status": "routing"
        }

    except Exception as e:
        logger.error(f"[{channel}] Judging failed: {str(e)}", exc_info=True)
        error_record = {
            "node": "judge_content",
            "channel": channel,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "internal_errors": state.get('internal_errors', []) + [error_record],
            "internal_status": "failed"
        }


def refine_content_node(state: ChannelState) -> Dict[str, Any]:
    """
    Node: Refine content based on judge feedback

    Args:
        state: Current channel state with judge_results

    Returns:
        Updated state with refined current_content
    """
    channel = state['channel_name']
    logger.info(f"=== REFINE CONTENT NODE [{channel}] ===")

    try:
        # Initialize agent
        agent = ContentAgent(
            channel=channel,
            max_refinement_iterations=state['max_iterations'],
            api_config={
                'model': state['input_config'].get('api_model', 'gemini-2.5-flash'),
                'temperature': state['input_config'].get('api_temperature', 0.7),
                'max_output_tokens': state['input_config'].get('api_max_tokens', 64000),
                'max_retries': state['input_config'].get('api_max_retries', 3),
                'retry_delay': state['input_config'].get('api_retry_delay', 2),
            }
        )

        # Get latest judge result
        latest_judge = state['judge_results'][-1]

        # Refine content
        refined_content = agent.refine(state['current_content'], latest_judge)

        logger.info(f"[{channel}] Content refined (iteration {state['current_iteration'] + 1})")

        # Update refinement history
        refinement_history = state.get('refinement_history', []).copy()
        refinement_history.append({
            "iteration": state['current_iteration'] + 1,
            "score": latest_judge.get('score', 0),
            "feedback": latest_judge.get('feedback', {})
        })

        # Estimate tokens
        estimated_tokens = len(json.dumps(refined_content)) // 4

        return {
            "current_content": refined_content,
            "current_iteration": state['current_iteration'] + 1,
            "refinement_history": refinement_history,
            "tokens_used": state.get('tokens_used', 0) + estimated_tokens,
            "api_calls": state.get('api_calls', 0) + 1,
            "internal_status": "judging"
        }

    except Exception as e:
        logger.error(f"[{channel}] Refinement failed: {str(e)}", exc_info=True)
        error_record = {
            "node": "refine_content",
            "channel": channel,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "internal_errors": state.get('internal_errors', []) + [error_record],
            "internal_status": "failed"
        }


def finalize_channel_node(state: ChannelState) -> Dict[str, Any]:
    """
    Node: Finalize channel output with metadata

    Args:
        state: Current channel state

    Returns:
        Updated state with final content and metadata
    """
    channel = state['channel_name']
    logger.info(f"=== FINALIZE CHANNEL NODE [{channel}] ===")

    try:
        # Get latest judge result
        latest_judge = state['judge_results'][-1] if state.get('judge_results') else {}

        # Calculate generation time
        start_time = datetime.fromisoformat(state['generation_start_time'])
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()

        logger.info(f"[{channel}] Finalized - Score: {latest_judge.get('score', 0)}/10, Time: {generation_time:.1f}s")

        return {
            "final_content": state['current_content'],
            "final_score": latest_judge.get('score', 0),
            "passed_quality": latest_judge.get('passes_quality', False),
            "final_feedback": latest_judge.get('feedback', {}),
            "generation_end_time": end_time.isoformat(),
            "generation_time": generation_time,
            "internal_status": "finalized"
        }

    except Exception as e:
        logger.error(f"[{channel}] Finalization failed: {str(e)}", exc_info=True)
        error_record = {
            "node": "finalize_channel",
            "channel": channel,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return {
            "internal_errors": state.get('internal_errors', []) + [error_record],
            "internal_status": "failed"
        }


# ============================================================================
# ROUTER FUNCTIONS
# ============================================================================

def quality_router(state: ChannelState) -> str:
    """
    Router: Determine next step based on quality check

    Args:
        state: Current channel state

    Returns:
        Next node name: "finalize" or "refine"
    """
    if not state.get('judge_results'):
        logger.warning("quality_router called without judge results")
        return "finalize"

    latest_judge = state['judge_results'][-1]
    current_iteration = state['current_iteration']
    max_iterations = state['max_iterations']

    # Check if passed quality
    if latest_judge.get('passes_quality', False):
        logger.info(f"[{state['channel_name']}] Quality check PASSED")
        return "finalize"

    # Check if max iterations reached
    if current_iteration >= max_iterations:
        logger.warning(f"[{state['channel_name']}] Max iterations reached, finalizing anyway")
        return "finalize"

    # Needs refinement
    logger.info(f"[{state['channel_name']}] Quality check FAILED, refining...")
    return "refine"

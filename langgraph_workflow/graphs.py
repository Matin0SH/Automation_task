"""
Graph Definitions for LangGraph Workflow

Key fix: Subgraph results are collected via Send API return values,
NOT by merging ChannelState back into WorkflowState.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END, START
from langgraph.types import Send

# Import state schemas
from .state import WorkflowState, ChannelState, ChannelResult, create_initial_channel_state

# Import nodes
from .nodes import (
    # Main workflow nodes
    parse_documents_node,
    aggregate_results_node,
    save_results_node,

    # Channel subgraph nodes
    load_context_node,
    generate_content_node,
    judge_content_node,
    refine_content_node,
    finalize_channel_node,

    # Routers
    quality_router
)

logger = logging.getLogger(__name__)


# ============================================================================
# CHANNEL SUBGRAPH
# ============================================================================

def create_channel_subgraph():
    """
    Create quality control subgraph for a single channel

    Workflow:
    START → load_context → generate → judge → quality_router
                                                ├─ pass → finalize → END
                                                └─ fail → refine → judge (loop)

    Returns:
        Compiled StateGraph for channel processing
    """
    # Create graph with ChannelState
    subgraph = StateGraph(ChannelState)

    # Add nodes
    subgraph.add_node("load_context", load_context_node)
    subgraph.add_node("generate", generate_content_node)
    subgraph.add_node("judge", judge_content_node)
    subgraph.add_node("refine", refine_content_node)
    subgraph.add_node("finalize", finalize_channel_node)

    # Define edges
    subgraph.add_edge(START, "load_context")
    subgraph.add_edge("load_context", "generate")
    subgraph.add_edge("generate", "judge")

    # Conditional routing after judge
    subgraph.add_conditional_edges(
        "judge",
        quality_router,
        {
            "finalize": "finalize",
            "refine": "refine",
        }
    )

    # Refine loops back to judge
    subgraph.add_edge("refine", "judge")

    # Finalize ends subgraph
    subgraph.add_edge("finalize", END)

    return subgraph.compile()


# ============================================================================
# MAIN WORKFLOW GRAPH
# ============================================================================

def route_to_channels(state: WorkflowState) -> List[Send]:
    """
    Router: Send work to multiple channels in parallel

    This function creates Send commands for each channel, which will
    execute the channel subgraphs in parallel.

    IMPORTANT: Each Send command creates an independent channel state.
    The subgraph results are NOT automatically merged back into WorkflowState.

    Args:
        state: Current workflow state

    Returns:
        List of Send commands for parallel execution
    """
    channels = state['channels']
    config = state['config']
    parsed_docs = state['parsed_documents']

    if not parsed_docs:
        logger.error("No parsed documents available for channel routing")
        return []

    # Extract documents dict
    documents = parsed_docs.get('documents', {})

    # Load examples for each channel
    def load_examples(channel_name: str) -> List[Dict]:
        """Load examples from examples folder"""
        examples = []
        examples_dir = Path(f"examples/{channel_name}")

        if not examples_dir.exists():
            logger.warning(f"Examples directory not found: {examples_dir}")
            return examples

        for example_file in examples_dir.glob('*.json'):
            try:
                with open(example_file, 'r', encoding='utf-8') as f:
                    example_data = json.load(f)
                    examples.append(example_data)
            except Exception as e:
                logger.warning(f"Failed to load example {example_file}: {str(e)}")

        logger.info(f"Loaded {len(examples)} examples for {channel_name}")
        return examples

    # Create Send commands for each channel
    send_commands = []
    for channel in channels:
        # Create initial channel state
        channel_state = create_initial_channel_state(
            channel_name=channel,
            topic=state['topic'],
            documents=documents,
            examples=load_examples(channel),
            config=config
        )

        # Create Send command to route to channel subgraph
        send_commands.append(
            Send(f"channel_{channel}", channel_state)
        )

        logger.info(f"Routing to channel_{channel}")

    return send_commands


def collect_channel_results_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Node: Collect results from parallel channel subgraphs

    This node is called AFTER all channel subgraphs complete.
    It extracts the final ChannelState from each subgraph and
    transforms it into a ChannelResult for storage in WorkflowState.

    CRITICAL: This is where we transform ChannelState → ChannelResult

    Args:
        state: Current workflow state

    Returns:
        Updated state with channel_results populated
    """
    logger.info("=== COLLECT CHANNEL RESULTS NODE ===")

    # When using Send API, the channel subgraph results are stored
    # in the state under keys like "channel_linkedin", "channel_newsletter", etc.
    # We need to extract them and build ChannelResult objects.

    collected_results: Dict[str, ChannelResult] = {}

    # Get channels from state
    channels = state.get('channels', [])

    for channel in channels:
        # The channel subgraph result is stored under "channel_{name}"
        # But this is NOT in the state yet - we need to receive it
        # from the subgraph's return value

        # For now, we'll check if channel_results already exists
        # (populated by the graph's automatic state merging)
        pass

    # Actually, with Send API, we need a different approach
    # The subgraph states are passed as a list to the next node
    # So this node will receive them as input

    return {
        "current_phase": "aggregating"
    }


# This is a wrapper node that properly extracts channel results
def build_channel_result_from_state(channel_state: ChannelState) -> ChannelResult:
    """
    Convert ChannelState to ChannelResult

    Args:
        channel_state: Final state from channel subgraph

    Returns:
        ChannelResult object
    """
    return ChannelResult(
        channel_name=channel_state['channel_name'],
        final_content=channel_state.get('final_content'),
        final_score=channel_state.get('final_score', 0),
        passed_quality=channel_state.get('passed_quality', False),
        refinement_iterations=channel_state.get('current_iteration', 0),
        refinement_history=channel_state.get('refinement_history', []),
        final_feedback=channel_state.get('final_feedback', {}),
        tokens_used=channel_state.get('tokens_used', 0),
        api_calls=channel_state.get('api_calls', 0),
        generation_time=channel_state.get('generation_time', 0.0),
        model_used=channel_state.get('model_used', 'gemini-2.5-flash'),
        errors=channel_state.get('internal_errors', [])
    )


def create_channel_wrapper_node(channel_name: str, subgraph):
    """
    Create a wrapper node that:
    1. Invokes the channel subgraph
    2. Transforms ChannelState result to ChannelResult
    3. Updates WorkflowState.channel_results

    This ensures clean state separation.

    Args:
        channel_name: Name of channel
        subgraph: Compiled channel subgraph

    Returns:
        Wrapper function that can be added as a node
    """
    def wrapper_node(state: WorkflowState) -> Dict[str, Any]:
        """Wrapper node for channel subgraph"""
        logger.info(f"=== CHANNEL WRAPPER [{channel_name}] ===")

        # Extract data from WorkflowState
        parsed_docs = state['parsed_documents']
        documents = parsed_docs.get('documents', {})

        # Load examples
        examples = []
        examples_dir = Path(f"examples/{channel_name}")
        if examples_dir.exists():
            for example_file in examples_dir.glob('*.json'):
                try:
                    with open(example_file, 'r', encoding='utf-8') as f:
                        examples.append(json.load(f))
                except Exception as e:
                    logger.warning(f"Failed to load example: {e}")

        # Create ChannelState
        channel_state = create_initial_channel_state(
            channel_name=channel_name,
            topic=state['topic'],
            documents=documents,
            examples=examples,
            config=state['config']
        )

        # Invoke subgraph
        final_channel_state = subgraph.invoke(channel_state)

        # Transform to ChannelResult
        channel_result = build_channel_result_from_state(final_channel_state)

        # Update WorkflowState.channel_results
        channel_results = state.get('channel_results', {}).copy()
        channel_results[channel_name] = channel_result

        logger.info(f"[{channel_name}] Result collected: score={channel_result['final_score']}/10")

        return {
            "channel_results": channel_results
        }

    return wrapper_node


def create_main_graph():
    """
    Create main workflow graph with proper state separation

    Workflow:
    START → parse_documents → route_channels (parallel wrappers)
                ├─ channel_linkedin_wrapper
                ├─ channel_newsletter_wrapper
                └─ channel_blog_wrapper
            → aggregate_results → save_results → END

    Each wrapper:
    1. Extracts data from WorkflowState
    2. Creates ChannelState
    3. Invokes channel subgraph
    4. Transforms result to ChannelResult
    5. Updates WorkflowState.channel_results

    Returns:
        Compiled StateGraph for main workflow
    """
    # Create graph with WorkflowState
    graph = StateGraph(WorkflowState)

    # Create channel subgraph
    channel_subgraph = create_channel_subgraph()

    # Add main workflow nodes
    graph.add_node("parse_documents", parse_documents_node)
    graph.add_node("aggregate_results", aggregate_results_node)
    graph.add_node("save_results", save_results_node)

    # Add channel wrapper nodes (NOT raw subgraphs)
    for channel in ["linkedin", "newsletter", "blog"]:
        wrapper = create_channel_wrapper_node(channel, channel_subgraph)
        graph.add_node(f"channel_{channel}", wrapper)

    # Define edges
    graph.add_edge(START, "parse_documents")

    # After parsing, route to all channels in parallel
    graph.add_edge("parse_documents", "channel_linkedin")
    graph.add_edge("parse_documents", "channel_newsletter")
    graph.add_edge("parse_documents", "channel_blog")

    # All channels converge to aggregator
    graph.add_edge(["channel_linkedin", "channel_newsletter", "channel_blog"], "aggregate_results")

    # Then save and end
    graph.add_edge("aggregate_results", "save_results")
    graph.add_edge("save_results", END)

    return graph.compile()


# ============================================================================
# GRAPH WITH CHECKPOINTING
# ============================================================================

def create_main_graph_with_checkpointing(checkpointer):
    """
    Create main workflow graph with checkpointing enabled

    Args:
        checkpointer: Checkpointer instance (MemorySaver or PostgresSaver)

    Returns:
        Compiled StateGraph with checkpointing
    """
    # Create the same graph structure
    graph = StateGraph(WorkflowState)

    # Create channel subgraph
    channel_subgraph = create_channel_subgraph()

    # Add main workflow nodes
    graph.add_node("parse_documents", parse_documents_node)
    graph.add_node("aggregate_results", aggregate_results_node)
    graph.add_node("save_results", save_results_node)

    # Add channel wrapper nodes
    for channel in ["linkedin", "newsletter", "blog"]:
        wrapper = create_channel_wrapper_node(channel, channel_subgraph)
        graph.add_node(f"channel_{channel}", wrapper)

    # Define edges
    graph.add_edge(START, "parse_documents")
    graph.add_edge("parse_documents", "channel_linkedin")
    graph.add_edge("parse_documents", "channel_newsletter")
    graph.add_edge("parse_documents", "channel_blog")
    graph.add_edge(["channel_linkedin", "channel_newsletter", "channel_blog"], "aggregate_results")
    graph.add_edge("aggregate_results", "save_results")
    graph.add_edge("save_results", END)

    # Compile with checkpointer
    return graph.compile(checkpointer=checkpointer)

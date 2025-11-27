"""
State Schema Definitions for LangGraph Workflow

CRITICAL: WorkflowState and ChannelState have ZERO overlapping keys
to prevent InvalidUpdateError when parallel subgraphs complete.

Keys that receive concurrent updates from parallel nodes use Annotated
with custom reducer functions.
"""

from typing import TypedDict, Dict, List, Optional, Any, Annotated
from datetime import datetime


# ============================================================================
# REDUCER FUNCTIONS
# ============================================================================

def merge_channel_results(existing: Dict[str, "ChannelResult"],
                          new: Dict[str, "ChannelResult"]) -> Dict[str, "ChannelResult"]:
    """
    Reducer: Merge channel results from parallel nodes

    When multiple channel wrapper nodes complete in parallel, each returns
    an update to channel_results. This reducer merges them into a single dict.

    Args:
        existing: Current channel_results dict
        new: New channel_results dict from a parallel node

    Returns:
        Merged dict with all channel results
    """
    merged = existing.copy() if existing else {}
    merged.update(new)
    return merged


# ============================================================================
# CHANNEL RESULT (returned from subgraph to parent)
# ============================================================================

class ChannelResult(TypedDict, total=False):
    """
    Result from a single channel generation.
    This is what gets stored in WorkflowState.channel_results
    """
    channel_name: str
    final_content: Optional[Dict[str, Any]]
    final_score: float
    passed_quality: bool
    refinement_iterations: int
    refinement_history: List[Dict[str, Any]]
    final_feedback: Dict[str, Any]
    tokens_used: int
    api_calls: int
    generation_time: float
    model_used: str
    errors: List[Dict[str, Any]]


# ============================================================================
# WORKFLOW STATE (Parent Graph)
# ============================================================================

class WorkflowState(TypedDict, total=False):
    """
    Global workflow state for the main graph.

    This state is shared across parse_documents, aggregate_results,
    and save_results nodes. It does NOT share any keys with ChannelState.

    CRITICAL: channel_results uses Annotated with merge_channel_results
    reducer to handle concurrent updates from parallel channel wrapper nodes.
    """
    # Input configuration
    topic: str
    channels: List[str]
    config: Dict[str, Any]

    # Parsed documents (from TopicParser)
    parsed_documents: Optional[Dict[str, Any]]

    # Results from channel subgraphs (collected after parallel execution)
    # Uses custom reducer to merge updates from parallel channel nodes
    channel_results: Annotated[Dict[str, ChannelResult], merge_channel_results]

    # Aggregated metrics (calculated from all channel results)
    total_tokens_used: int
    total_api_calls: int
    total_cost: float

    # Timestamps
    start_time: str
    end_time: Optional[str]

    # Workflow status
    status: str  # 'running', 'completed', 'failed'
    current_phase: str  # 'parsing', 'generating', 'aggregating', 'saving'

    # Errors from main workflow nodes (NOT from channels)
    errors: List[Dict[str, Any]]


# ============================================================================
# CHANNEL STATE (Subgraph)
# ============================================================================

class ChannelState(TypedDict, total=False):
    """
    Per-channel subgraph state.

    IMPORTANT: This state has ZERO overlapping keys with WorkflowState.
    Each channel subgraph operates independently with this state.

    The final state is NOT merged back into WorkflowState. Instead,
    it's collected by aggregate_results_node and transformed into
    a ChannelResult object.
    """
    # Channel identity
    channel_name: str

    # Input context (passed from parent, read-only)
    input_topic: str
    input_documents: Dict[str, str]
    input_examples: List[Dict[str, Any]]
    input_config: Dict[str, Any]

    # Generation state
    current_content: Optional[Dict[str, Any]]
    current_iteration: int
    max_iterations: int

    # Quality control
    judge_results: List[Dict[str, Any]]
    refinement_history: List[Dict[str, Any]]
    quality_threshold: float

    # Final output
    final_content: Optional[Dict[str, Any]]
    final_score: float
    passed_quality: bool
    final_feedback: Dict[str, Any]

    # Metadata
    tokens_used: int
    api_calls: int
    generation_start_time: str
    generation_end_time: Optional[str]
    generation_time: float
    model_used: str

    # Internal state (not exposed to parent)
    internal_errors: List[Dict[str, Any]]
    internal_status: str  # 'initializing', 'generating', 'judging', 'refining', 'finalized'
    using_fallback: bool


# ============================================================================
# INITIAL STATE FACTORIES
# ============================================================================

def create_initial_workflow_state(
    topic: str,
    channels: List[str],
    config: Dict[str, Any]
) -> WorkflowState:
    """
    Create initial workflow state with default values.

    Args:
        topic: Topic name
        channels: List of channels to process
        config: Configuration dictionary

    Returns:
        Initialized WorkflowState
    """
    return WorkflowState(
        topic=topic,
        channels=channels,
        config=config,
        parsed_documents=None,
        channel_results={},
        total_tokens_used=0,
        total_api_calls=0,
        total_cost=0.0,
        start_time=datetime.now().isoformat(),
        end_time=None,
        status='running',
        current_phase='parsing',
        errors=[]
    )


def create_initial_channel_state(
    channel_name: str,
    topic: str,
    documents: Dict[str, str],
    examples: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> ChannelState:
    """
    Create initial channel state for a subgraph.

    Args:
        channel_name: Name of channel (linkedin, newsletter, blog)
        topic: Topic name
        documents: Parsed documents dict
        examples: Few-shot examples
        config: Configuration dict

    Returns:
        Initialized ChannelState
    """
    return ChannelState(
        channel_name=channel_name,
        input_topic=topic,
        input_documents=documents,
        input_examples=examples,
        input_config=config,
        current_content=None,
        current_iteration=0,
        max_iterations=config.get('max_refinement_iterations', 2),
        judge_results=[],
        refinement_history=[],
        quality_threshold=config.get('quality_threshold', 8.0),
        final_content=None,
        final_score=0.0,
        passed_quality=False,
        final_feedback={},
        tokens_used=0,
        api_calls=0,
        generation_start_time=datetime.now().isoformat(),
        generation_end_time=None,
        generation_time=0.0,
        model_used=config.get('api_model', 'gemini-2.5-flash'),
        internal_errors=[],
        internal_status='initializing',
        using_fallback=False
    )

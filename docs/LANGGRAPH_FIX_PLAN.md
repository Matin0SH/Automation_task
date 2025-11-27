# LangGraph Implementation Fix Plan

## Problem Analysis

### Error
```
langgraph.errors.InvalidUpdateError: At key 'topic': Can receive only one value per step.
Use an Annotated key to handle multiple values.
```

### Root Cause
When using LangGraph's `Send` API with parallel subgraphs:
1. Three channel subgraphs (LinkedIn, Newsletter, Blog) execute in parallel
2. Each subgraph has its own `ChannelState` with fields like `topic`, `errors`, `status`
3. When subgraphs complete, LangGraph tries to merge their state back into the parent `WorkflowState`
4. Since all three subgraphs try to update the same keys simultaneously (e.g., `topic`), we get the InvalidUpdateError

### The Fundamental Mistake

**Current broken architecture:**
- `WorkflowState` has keys: `topic`, `errors`, `status`, `channel_results`, etc.
- `ChannelState` ALSO has keys: `topic`, `errors`, `status`, etc.
- When parallel subgraphs complete, they all try to update the same WorkflowState keys → CONFLICT

**The problem:** Overlapping state keys between parent and subgraph states

## Solution Approach

Based on LangGraph best practices, there are **two valid approaches**:

### Approach 1: Separate State Schemas (RECOMMENDED)
- ChannelState and WorkflowState have **completely different** key names
- No overlap = no conflicts
- Subgraphs work independently
- Aggregate results in a dedicated collector node

### Approach 2: Use Annotated Reducers
- Keep overlapping keys but use `Annotated[type, reducer]` for keys that receive concurrent updates
- Use reducers like `operator.add` for lists, custom reducer for dicts
- More complex but allows shared state

## Recommended Fix: Approach 1 (Clean Separation)

### Key Changes

#### 1. WorkflowState (Parent Graph State)
```python
class WorkflowState(TypedDict):
    # Input
    topic: str
    channels: List[str]
    config: Dict[str, Any]

    # Parsed documents
    parsed_documents: Optional[Dict[str, Any]]

    # Results from ALL channels (collected after parallel execution)
    channel_results: Dict[str, ChannelResult]  # Key: channel name

    # Aggregated metrics
    total_tokens: int
    total_cost: float
    total_api_calls: int

    # Status
    status: str
    current_phase: str
    errors: List[Dict]
```

#### 2. ChannelState (Subgraph State - NO OVERLAP)
```python
class ChannelState(TypedDict):
    # Identity
    channel_name: str

    # Input context (read-only from parent)
    input_topic: str
    input_documents: Dict[str, str]
    input_examples: List[Dict]
    input_config: Dict[str, Any]

    # Generation process
    current_content: Optional[Dict]
    current_iteration: int

    # Quality control
    judge_results: List[Dict]
    refinement_history: List[Dict]

    # Final output
    final_content: Optional[Dict]
    final_score: float
    passed_quality: bool

    # Metadata
    tokens_used: int
    api_calls: int
    generation_time: float
    model_used: str

    # Internal status (NOT merged back to parent)
    internal_errors: List[Dict]
    internal_status: str
```

**Key differences:**
- NO `topic` (uses `input_topic` instead)
- NO `errors` (uses `internal_errors`)
- NO `status` (uses `internal_status`)
- NO overlap with WorkflowState keys

#### 3. Graph Structure

**Main Graph:**
```
START
  → parse_documents
  → route_to_channels (Send API - parallel execution)
      ├─ channel_linkedin (subgraph)
      ├─ channel_newsletter (subgraph)
      └─ channel_blog (subgraph)
  → collect_results (aggregate from subgraphs)
  → save_results
  → END
```

**Channel Subgraph:**
```
START
  → load_context
  → generate
  → judge
  → quality_router
      ├─ PASS → finalize → END
      └─ FAIL → refine → judge (loop)
```

#### 4. Result Collection

The `collect_results` node:
- Receives the WorkflowState after all channel subgraphs complete
- Extracts final channel states from subgraph outputs
- Builds `ChannelResult` objects
- Updates `WorkflowState.channel_results`

**CRITICAL:** Subgraphs do NOT update WorkflowState directly. They only update their own ChannelState.

## Implementation Steps

### Step 1: Fix State Schemas
- [ ] Rewrite `WorkflowState` with clean keys
- [ ] Rewrite `ChannelState` with NO overlapping keys
- [ ] Update `ChannelResult` TypedDict

### Step 2: Fix Nodes
- [ ] Update all channel nodes to use new ChannelState keys:
  - `load_context_node`
  - `generate_content_node`
  - `judge_content_node`
  - `refine_content_node`
  - `finalize_channel_node`

### Step 3: Fix Graph Routing
- [ ] Update `route_to_channels` to properly map WorkflowState → ChannelState
- [ ] Implement proper `collect_results` node to extract subgraph outputs
- [ ] Ensure subgraphs return ONLY ChannelState updates

### Step 4: Test
- [ ] Test single channel: `python main_langgraph.py linkedin`
- [ ] Test all channels parallel: `python main_langgraph.py --all-channels`
- [ ] Verify no InvalidUpdateError
- [ ] Verify results are correctly aggregated

## Files to Modify

1. `langgraph_workflow/state.py` - Fix state schemas (complete rewrite)
2. `langgraph_workflow/nodes.py` - Update all nodes to use new state keys
3. `langgraph_workflow/graphs.py` - Fix routing and result collection
4. `main_langgraph.py` - May need minor updates

## Testing Checklist

After fix:
- [ ] Single channel works (LinkedIn)
- [ ] All channels in parallel works
- [ ] Quality scores maintained (9-10/10)
- [ ] Results saved correctly (JSON + Markdown)
- [ ] No state conflicts
- [ ] Checkpointing works

## References

- [LangGraph Issue #2336 - InvalidUpdateError with parallel processing](https://github.com/langchain-ai/langgraph/issues/2336)
- [LangGraph Issue #1964 - Sink node with parallel subgraphs](https://github.com/langchain-ai/langgraph/issues/1964)
- [LangGraph Error Docs - INVALID_CONCURRENT_GRAPH_UPDATE](https://langchain-ai.github.io/langgraph/troubleshooting/errors/INVALID_CONCURRENT_GRAPH_UPDATE/)

## Next Action

Clean rewrite of the LangGraph implementation with proper state separation.

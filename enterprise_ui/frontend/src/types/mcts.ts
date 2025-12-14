/**
 * MCTS (Monte Carlo Tree Search) types
 *
 * TypeScript definitions mirroring Python models from:
 * - src/reasoning_trading/mcts/node.py
 * - src/reasoning_trading/langgraph/state.py
 */

import type { TradingAction } from './actions';
import type { TradingState } from './trading';

/**
 * MCTS execution phases
 */
export enum MCTSPhase {
  SELECTION = 'selection',
  EXPANSION = 'expansion',
  SIMULATION = 'simulation',
  BACKPROPAGATION = 'backpropagation',
  COMPLETE = 'complete',
  ERROR = 'error',
}

/**
 * MCTS tree node for trading decisions
 *
 * Stores the state, action that led to this state, and statistics
 * needed for UCB selection and value backpropagation.
 */
export interface MCTSNode {
  // Unique identifier
  id: string;

  // State representation
  state: TradingState | null;

  // Action that led to this state (null for root)
  action: TradingAction | null;

  // Tree structure
  parent_id: string | null;
  children_ids: string[];

  // LLM interaction
  /** Conversation history for LLM context */
  messages: Array<{
    role: 'system' | 'user' | 'assistant';
    content: string;
  }>;
  /** Self-evaluation from LLM */
  reflection: string;

  // Value estimation (Sharpe ratio scale, typically -3 to 3)
  value: number;

  // Visit statistics
  visits: number;
  value_sum: number;

  // Q-value for action selection (cumulative discounted reward)
  q_value: number;

  // Prior probability from policy network (0-1)
  prior: number;

  // Terminal state flags
  is_solved: boolean;
  is_terminal: boolean;

  // Metadata
  depth: number;
  created_at: string;
}

/**
 * Information about an MCTS tree node (simplified for serialization)
 */
export interface NodeInfo {
  node_id: string;
  parent_id: string | null;
  action: string;
  visit_count: number;
  value_sum: number;
  prior: number;
  children: string[];
  is_terminal: boolean;
  is_expanded: boolean;
  level: string;
}

/**
 * Result from selection phase
 */
export interface SelectionResult {
  selected_path: string[];
  leaf_node_id: string;
  uct_values: Record<string, number>;
  needs_expansion: boolean;
  is_terminal: boolean;
}

/**
 * Result from expansion phase
 */
export interface ExpansionResult {
  expanded_node_id: string;
  new_children: string[];
  policy_priors: Record<string, number>;
  action_mask: boolean[];
  expansion_time_ms: number;
}

/**
 * Result from simulation phase
 */
export interface SimulationResult {
  rollout_values: number[];
  mean_value: number;
  std_value: number;
  num_simulations: number;
  simulation_time_ms: number;
  terminal_states: Array<Record<string, unknown>>;
}

/**
 * Result from backpropagation phase
 */
export interface BackpropResult {
  updated_nodes: string[];
  value_deltas: Record<string, number>;
  visit_increments: Record<string, number>;
  backprop_time_ms: number;
}

/**
 * State for LangGraph MCTS orchestration
 *
 * Contains all information needed for MCTS phase transitions.
 */
export interface MCTSState {
  // Current phase
  phase: MCTSPhase;
  iteration: number;
  max_iterations: number;

  // Tree structure
  root_node_id: string;
  nodes: Record<string, NodeInfo>;
  current_node_id: string;

  // Trading state
  trading_state_features: number[] | null;
  symbol: string;
  hierarchy_level: string;

  // Phase results
  selection_result: SelectionResult | null;
  expansion_result: ExpansionResult | null;
  simulation_result: SimulationResult | null;
  backprop_result: BackpropResult | null;

  // Search configuration
  exploration_constant: number;
  temperature: number;
  use_policy_prior: boolean;
  parallel_simulations: number;

  // Timing
  start_time: string;
  phase_times: Record<string, number>;

  // Error handling
  error_message: string | null;
  retry_count: number;
  max_retries: number;

  // Results
  best_action: string | null;
  action_probabilities: Record<string, number>;
  root_value: number;
}

/**
 * MCTS tree representation
 */
export interface MCTSTree {
  root: MCTSNode;
  nodes: Record<string, MCTSNode>;
  total_simulations: number;
  start_time: string;
  end_time: string | null;
}

/**
 * Final MCTS result with best action and statistics
 */
export interface MCTSResult {
  // Best action selected
  best_action: TradingAction;

  // Alternative actions considered
  action_distribution: Array<{
    action: TradingAction;
    visit_count: number;
    mean_value: number;
    probability: number;
  }>;

  // Tree statistics
  total_simulations: number;
  tree_depth: number;
  total_nodes: number;

  // Values and confidence
  root_value: number;
  confidence: number;

  // Timing
  computation_time_ms: number;
  phase_times: Record<MCTSPhase, number>;

  // Metadata
  symbol: string;
  timestamp: string;
}

/**
 * UCB (Upper Confidence Bound) calculation parameters
 */
export interface UCBParams {
  /** Exploration weight (typically sqrt(2) = 1.414) */
  exploration_constant: number;
  /** Use PUCT (Predictor + UCB) with prior probabilities */
  use_prior: boolean;
  /** PUCT exploration constant */
  c_puct: number;
}

/**
 * Calculate UCB1 value for node selection
 *
 * Uses the formula: Q(s,a) + c * sqrt(ln(N(s)) / N(s,a))
 */
export function calculateUCB(
  node: MCTSNode,
  parentVisits: number,
  params: UCBParams
): number {
  if (node.visits === 0) {
    return Number.POSITIVE_INFINITY;
  }

  if (parentVisits === 0) {
    return node.value_sum / node.visits;
  }

  const exploitation = node.value_sum / node.visits;
  const exploration =
    params.exploration_constant * Math.sqrt(Math.log(parentVisits) / node.visits);

  return exploitation + exploration;
}

/**
 * Calculate PUCT (Predictor + UCB) value with prior probability
 *
 * Used when a policy network provides action priors:
 * Q(s,a) + c_puct * P(s,a) * sqrt(N(s)) / (1 + N(s,a))
 */
export function calculatePUCT(
  node: MCTSNode,
  parentVisits: number,
  params: UCBParams
): number {
  const meanValue = node.visits > 0 ? node.value_sum / node.visits : 0;

  if (!params.use_prior) {
    return meanValue;
  }

  const uValue =
    (params.c_puct * node.prior * Math.sqrt(parentVisits)) / (1 + node.visits);

  return meanValue + uValue;
}

/**
 * Type guard to check if a value is a valid MCTSPhase
 */
export function isMCTSPhase(value: string): value is MCTSPhase {
  return (
    value === MCTSPhase.SELECTION ||
    value === MCTSPhase.EXPANSION ||
    value === MCTSPhase.SIMULATION ||
    value === MCTSPhase.BACKPROPAGATION ||
    value === MCTSPhase.COMPLETE ||
    value === MCTSPhase.ERROR
  );
}

/**
 * Check if MCTS search is complete
 */
export function isSearchComplete(state: MCTSState): boolean {
  return (
    state.iteration >= state.max_iterations ||
    state.phase === MCTSPhase.COMPLETE ||
    state.phase === MCTSPhase.ERROR
  );
}

/**
 * Get total search time in milliseconds
 */
export function getTotalSearchTime(state: MCTSState): number {
  let total = 0;
  for (const key in state.phase_times) {
    if (state.phase_times.hasOwnProperty(key)) {
      total += state.phase_times[key];
    }
  }
  return total;
}

/**
 * Create a new MCTS node
 */
export function createMCTSNode(
  id: string,
  state: TradingState | null,
  action: TradingAction | null,
  parentId: string | null,
  depth: number = 0
): MCTSNode {
  return {
    id,
    state,
    action,
    parent_id: parentId,
    children_ids: [],
    messages: [],
    reflection: '',
    value: 0.0,
    visits: 0,
    value_sum: 0.0,
    q_value: 0.0,
    prior: 0.0,
    is_solved: false,
    is_terminal: false,
    depth,
    created_at: new Date().toISOString(),
  };
}

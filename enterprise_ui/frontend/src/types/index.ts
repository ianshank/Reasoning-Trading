/**
 * Central export point for all TypeScript type definitions
 *
 * This file re-exports all types from individual modules for convenient importing.
 *
 * Usage:
 *   import { TradingState, TradingAction, MCTSNode } from '@/types';
 */

// Trading state and market data
export type {
  TechnicalIndicators,
  AnalystSignals,
  PortfolioState,
  OHLCVData,
  TradingState,
  RegimeClassification,
  RegimeHistory,
} from './trading';

export {
  MarketRegime,
  isMarketRegime,
  isValidTechnicalIndicators,
  isValidAnalystSignals,
} from './trading';

// Regime detection types
export type {
  IndicatorContribution,
  RegimeHistoryEntry,
  TransitionMatrix,
  HMMState,
  RegimeFrequencyData,
  RegimeStrategyMapping,
  RegimeAlert,
  RegimeAlertConfig,
  RegimeStatistics,
} from './regime';

export {
  RegimeState,
  isRegimeState,
  getRegimeDisplayName,
  getRegimeColor,
} from './regime';

// Trading actions
export type {
  PositionSizeAction,
  StopLossAction,
  TradingAction,
  ActionSpaceConfig,
} from './actions';

export {
  TradingDirection,
  TimeHorizon,
  OrderType,
  TradingDirectionUtils,
  TimeHorizonUtils,
  isTradingDirection,
  isTimeHorizon,
  isValidPositionSize,
  isValidStopLoss,
  calculateRiskRewardRatio,
  createHoldAction,
} from './actions';

// MCTS types
export type {
  MCTSNode,
  NodeInfo,
  SelectionResult,
  ExpansionResult,
  SimulationResult,
  BackpropResult,
  MCTSState,
  MCTSTree,
  MCTSResult,
  UCBParams,
} from './mcts';

export {
  MCTSPhase,
  isMCTSPhase,
  isSearchComplete,
  getTotalSearchTime,
  calculateUCB,
  calculatePUCT,
  createMCTSNode,
} from './mcts';

// Portfolio types
export type {
  Position,
  RiskMetrics,
  PerformanceMetrics,
  PortfolioAllocation,
  Portfolio,
  PortfolioSummary,
  PortfolioValuePoint,
  PortfolioHistory,
} from './portfolio';

export {
  PositionStatus,
  PositionSide,
  isOpenPosition,
  isLongPosition,
  isShortPosition,
  calculatePositionPnlPct,
  calculateAllocationPct,
  getRiskLevel,
} from './portfolio';

// API types
export type {
  APIResponse,
  PaginatedResponse,
  APIError,
  GetTradingDecisionRequest,
  TradingDecisionResponse,
  ExecuteTradeRequest,
  ExecuteTradeResponse,
  GetPortfolioRequest,
  PortfolioResponse,
  GetPositionRequest,
  PositionResponse,
  GetMarketDataRequest,
  MarketDataResponse,
  GetRegimeRequest,
  RegimeResponse,
  StartMCTSRequest,
  MCTSStartedResponse,
  GetMCTSStatusRequest,
  MCTSStatusResponse,
  GetAnalyticsRequest,
  AnalyticsResponse,
  HealthResponse,
  ConfigResponse,
  RateLimitInfo,
} from './api';

export { isSuccessResponse, isErrorResponse } from './api';

// WebSocket types
export type {
  WSMessage,
  SubscribeMessage,
  UnsubscribeMessage,
  MarketDataUpdate,
  PriceUpdate,
  RegimeChangeUpdate,
  PortfolioUpdate,
  PositionUpdate,
  OrderUpdate,
  MCTSStartedUpdate,
  MCTSPhaseUpdate,
  MCTSNodeUpdate,
  MCTSCompletedUpdate,
  MCTSErrorUpdate,
  TradeSignalUpdate,
  TradeExecutedUpdate,
  RiskAlertUpdate,
  SystemAlertUpdate,
  WSConnectionStatus,
} from './websocket';

export {
  WSMessageType,
  WSChannel,
  AlertSeverity,
  WSConnectionState,
  isWSMessage,
  parseWSMessage,
  createWSMessage,
} from './websocket';

// Order types
export type {
  OrderBook,
  OrderBookLevel,
  OrderFormData,
  OrderSubmitRequest,
  Order,
  OrderExecution,
  OrderWithExecutions,
  OrderFilters,
  OrderHistory,
  OrderPreview,
  TradeWithSlippage,
  SlippageStats,
} from './orders';

export {
  OrderStatus,
  TimeInForce,
  OrderBookSide,
  isPendingOrder,
  isFilledOrder,
  isActiveOrder,
  getOrderFillPercentage,
  getOrderStatusColor,
  formatTimeInForce,
  validateOrderForm,
} from './orders';

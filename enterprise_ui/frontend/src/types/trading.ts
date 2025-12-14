/**
 * Trading state and market data types
 *
 * TypeScript definitions mirroring Python models from:
 * - src/reasoning_trading/core/state.py
 * - src/reasoning_trading/regime/detector.py
 */

/**
 * Market regime classification for strategy selection
 */
export enum MarketRegime {
  TRENDING_UP = 'trending_up',
  TRENDING_DOWN = 'trending_down',
  MEAN_REVERTING = 'mean_reverting',
  VOLATILE = 'volatile',
  LOW_VOLATILITY = 'low_volatility',
  UNKNOWN = 'unknown',
}

/**
 * Technical analysis indicators computed from price data
 */
export interface TechnicalIndicators {
  // Trend indicators
  /** 20-period Simple Moving Average */
  sma_20: number | null;
  /** 50-period Simple Moving Average */
  sma_50: number | null;
  /** 200-period Simple Moving Average */
  sma_200: number | null;
  /** 12-period Exponential Moving Average */
  ema_12: number | null;
  /** 26-period Exponential Moving Average */
  ema_26: number | null;

  // Momentum indicators
  /** 14-period RSI (0-100) */
  rsi_14: number | null;
  /** MACD line */
  macd: number | null;
  /** MACD signal line */
  macd_signal: number | null;
  /** MACD histogram */
  macd_histogram: number | null;

  // Volatility indicators
  /** 14-period Average True Range (>= 0) */
  atr_14: number | null;
  /** Bollinger Band upper */
  bollinger_upper: number | null;
  /** Bollinger Band middle */
  bollinger_middle: number | null;
  /** Bollinger Band lower */
  bollinger_lower: number | null;
  /** 20-day historical volatility (>= 0) */
  volatility_20: number | null;

  // Volume indicators
  /** 20-period Volume SMA */
  volume_sma_20: number | null;
  /** On-Balance Volume */
  obv: number | null;

  // Additional indicators
  /** 14-period ADX (0-100) */
  adx_14: number | null;
  /** 20-period Commodity Channel Index */
  cci_20: number | null;
  /** Stochastic %K (0-100) */
  stochastic_k: number | null;
  /** Stochastic %D (0-100) */
  stochastic_d: number | null;
}

/**
 * Aggregated signals from the multi-agent analyst system
 */
export interface AnalystSignals {
  // Individual analyst scores (-1 to 1 scale)
  /** Market analyst signal */
  market_analyst_score: number;
  /** News analyst signal */
  news_analyst_score: number;
  /** Social sentiment signal */
  social_sentiment_score: number;
  /** Fundamental analyst signal */
  fundamental_analyst_score: number;
  /** Macro analyst signal */
  macro_analyst_score: number;

  // Confidence levels (0 to 1)
  /** Market analyst confidence */
  market_analyst_confidence: number;
  /** News analyst confidence */
  news_analyst_confidence: number;
  /** Social sentiment confidence */
  social_sentiment_confidence: number;
  /** Fundamental analyst confidence */
  fundamental_analyst_confidence: number;
  /** Macro analyst confidence */
  macro_analyst_confidence: number;

  // Bull/Bear debate outcomes
  /** Bull/Bear debate consensus (-1 to 1) */
  researcher_consensus: number;
  /** Confidence in debate outcome (0 to 1) */
  debate_confidence: number;

  // Raw evidence packets (optional, for detailed analysis)
  /** Raw evidence from analysts */
  evidence_packets: Record<string, unknown>;
}

/**
 * Current portfolio state including positions and risk metrics
 */
export interface PortfolioState {
  // Cash and total value
  /** Available cash */
  cash_balance: number;
  /** Total portfolio value */
  portfolio_value: number;

  // Position tracking (symbol -> quantity)
  /** Current positions */
  positions: Record<string, number>;
  /** Position market values */
  position_values: Record<string, number>;
  /** Position cost bases */
  position_costs: Record<string, number>;

  // P&L tracking
  /** Unrealized profit/loss */
  unrealized_pnl: number;
  /** Today's realized P&L */
  realized_pnl_today: number;
  /** Total realized P&L */
  realized_pnl_total: number;

  // Risk metrics
  /** Margin currently used (>= 0) */
  margin_used: number;
  /** Available margin (>= 0) */
  margin_available: number;
  /** 95% daily Value at Risk */
  daily_var_95: number | null;
  /** Maximum drawdown (0 to 1) */
  max_drawdown: number;
  /** Current drawdown (0 to 1) */
  current_drawdown: number;

  // Concentration metrics
  /** Largest position as % of portfolio (0 to 1) */
  largest_position_pct: number;
  /** Number of open positions (>= 0) */
  position_count: number;
}

/**
 * OHLCV data point (Open, High, Low, Close, Volume)
 */
export interface OHLCVData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Complete state representation for MCTS tree nodes
 *
 * Captures everything relevant to making a trading decision,
 * including market data, portfolio state, analyst signals, and
 * tree search metadata.
 */
export interface TradingState {
  // Identity
  symbol: string;
  timestamp: string;

  // Market data
  current_price: number;
  /** OHLCV history array */
  ohlcv_history: OHLCVData[] | null;
  technical_indicators: TechnicalIndicators;

  // Portfolio
  portfolio: PortfolioState;

  // Agent signals
  analyst_signals: AnalystSignals;

  // Risk context
  /** Risk profile: conservative, moderate, aggressive */
  risk_profile: 'conservative' | 'moderate' | 'aggressive';

  // Market context
  market_regime: MarketRegime;

  // Simulation metadata
  simulation_step: number;
  is_terminal: boolean;
}

/**
 * Regime classification result from regime detector
 */
export interface RegimeClassification {
  regime: string;
  confidence: number;

  // Alternative classifications
  regime_probabilities: Record<string, number>;

  // Contributing factors
  hmm_regime: string | null;
  hmm_confidence: number;
  technical_regime: string | null;
  technical_confidence: number;

  // Metadata
  timestamp: string;
  symbol: string;
}

/**
 * History of regime classifications
 */
export interface RegimeHistory {
  classifications: RegimeClassification[];
  regime_durations: Record<string, number>;
  current_regime: string;
  current_regime_start: string;
}

/**
 * Type guard to check if a value is a valid MarketRegime
 */
export function isMarketRegime(value: string): value is MarketRegime {
  return (
    value === MarketRegime.TRENDING_UP ||
    value === MarketRegime.TRENDING_DOWN ||
    value === MarketRegime.MEAN_REVERTING ||
    value === MarketRegime.VOLATILE ||
    value === MarketRegime.LOW_VOLATILITY ||
    value === MarketRegime.UNKNOWN
  );
}

/**
 * Type guard to check if technical indicators are valid
 */
export function isValidTechnicalIndicators(
  indicators: Partial<TechnicalIndicators>
): indicators is TechnicalIndicators {
  // Check RSI bounds if present
  if (indicators.rsi_14 !== null && indicators.rsi_14 !== undefined) {
    if (indicators.rsi_14 < 0 || indicators.rsi_14 > 100) {
      return false;
    }
  }

  // Check ADX bounds if present
  if (indicators.adx_14 !== null && indicators.adx_14 !== undefined) {
    if (indicators.adx_14 < 0 || indicators.adx_14 > 100) {
      return false;
    }
  }

  // Check Stochastic bounds if present
  if (indicators.stochastic_k !== null && indicators.stochastic_k !== undefined) {
    if (indicators.stochastic_k < 0 || indicators.stochastic_k > 100) {
      return false;
    }
  }
  if (indicators.stochastic_d !== null && indicators.stochastic_d !== undefined) {
    if (indicators.stochastic_d < 0 || indicators.stochastic_d > 100) {
      return false;
    }
  }

  return true;
}

/**
 * Type guard to check if analyst signals are valid
 */
export function isValidAnalystSignals(
  signals: Partial<AnalystSignals>
): signals is AnalystSignals {
  const scores = [
    signals.market_analyst_score,
    signals.news_analyst_score,
    signals.social_sentiment_score,
    signals.fundamental_analyst_score,
    signals.macro_analyst_score,
    signals.researcher_consensus,
  ];

  // Check all scores are in [-1, 1] range
  for (const score of scores) {
    if (score !== undefined && (score < -1 || score > 1)) {
      return false;
    }
  }

  const confidences = [
    signals.market_analyst_confidence,
    signals.news_analyst_confidence,
    signals.social_sentiment_confidence,
    signals.fundamental_analyst_confidence,
    signals.macro_analyst_confidence,
    signals.debate_confidence,
  ];

  // Check all confidences are in [0, 1] range
  for (const confidence of confidences) {
    if (confidence !== undefined && (confidence < 0 || confidence > 1)) {
      return false;
    }
  }

  return true;
}

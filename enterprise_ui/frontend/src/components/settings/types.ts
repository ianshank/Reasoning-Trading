/**
 * TypeScript types for settings configuration.
 * Mirrors the Python config structure from src/reasoning_trading/config.py
 */

export enum TradingMode {
  PAPER = 'paper',
  LIVE = 'live',
}

export enum RiskProfile {
  CONSERVATIVE = 'conservative',
  MODERATE = 'moderate',
  AGGRESSIVE = 'aggressive',
}

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
  CRITICAL = 'CRITICAL',
}

export enum OrderType {
  MARKET = 'market',
  LIMIT = 'limit',
  STOP = 'stop',
  STOP_LIMIT = 'stop_limit',
}

export enum TimeInForce {
  DAY = 'day',
  GTC = 'gtc',
  IOC = 'ioc',
  FOK = 'fok',
}

export interface LLMSettings {
  openai_api_key: string | null;
  anthropic_api_key: string | null;
  deep_think_llm: string;
  quick_think_llm: string;
  langchain_tracing_v2: boolean;
  langchain_api_key: string | null;
  langchain_project: string;
}

export interface TradingSettings {
  api_key: string | null;
  secret_key: string | null;
  base_url: string;
  trading_mode: TradingMode;
}

export interface DataAPISettings {
  finnhub_api_key: string | null;
  fred_api_key: string | null;
  coindesk_api_key: string | null;
}

export interface MCTSSettings {
  max_simulations: number;
  exploration_weight: number;
  rollout_horizon_days: number;
  confidence_threshold: number;
  realtime_budget_ms: number;
  progressive_widening_alpha: number;
  discount_factor: number;
}

export interface RiskSettings {
  max_position_size_fraction: number;
  default_stop_loss_percent: number;
  max_daily_loss_percent: number;
  default_risk_profile: RiskProfile;
}

export interface CacheSettings {
  redis_url: string;
  cache_ttl_seconds: number;
}

export interface DebateSettings {
  max_debate_rounds: number;
  max_risk_discuss_rounds: number;
  enable_parallel_analysts: boolean;
  enable_online_tools: boolean;
}

export interface APISettings {
  host: string;
  port: number;
  cors_allowed_origins: string[];
  rate_limit: number;
}

export interface FeatureFlags {
  allow_shorts: boolean;
  enable_margin_trading: boolean;
  enable_crypto_trading: boolean;
  auto_execute_trades: boolean;
}

export interface LoggingSettings {
  level: LogLevel;
  json_format: boolean;
}

export interface NotificationSettings {
  email_notifications: boolean;
  push_notifications: boolean;
  regime_change_alerts: boolean;
  trade_execution_alerts: boolean;
  risk_threshold_alerts: boolean;
  alert_threshold_percent: number;
}

export interface TradingPreferences {
  default_order_type: OrderType;
  default_time_in_force: TimeInForce;
}

export interface Settings {
  llm: LLMSettings;
  trading: TradingSettings;
  data_apis: DataAPISettings;
  mcts: MCTSSettings;
  risk: RiskSettings;
  cache: CacheSettings;
  debate: DebateSettings;
  api: APISettings;
  features: FeatureFlags;
  logging: LoggingSettings;
  notifications: NotificationSettings;
  trading_preferences: TradingPreferences;
}

export interface APIKeyStatus {
  openai: 'valid' | 'invalid' | 'expired' | 'not_set';
  anthropic: 'valid' | 'invalid' | 'expired' | 'not_set';
  alpaca: 'valid' | 'invalid' | 'expired' | 'not_set';
  finnhub: 'valid' | 'invalid' | 'expired' | 'not_set';
  fred: 'valid' | 'invalid' | 'expired' | 'not_set';
  coindesk: 'valid' | 'invalid' | 'expired' | 'not_set';
}

export interface CacheStats {
  total_keys: number;
  used_memory: string;
  hit_rate: number;
  total_hits: number;
  total_misses: number;
}

export interface MCTSPreset {
  name: string;
  description: string;
  settings: Partial<MCTSSettings>;
}

export const MCTS_PRESETS: MCTSPreset[] = [
  {
    name: 'Conservative',
    description: 'Deep exploration with high confidence threshold',
    settings: {
      max_simulations: 2000,
      exploration_weight: 2.0,
      confidence_threshold: 0.90,
      rollout_horizon_days: 60,
      realtime_budget_ms: 1000,
    },
  },
  {
    name: 'Balanced',
    description: 'Standard settings for typical trading scenarios',
    settings: {
      max_simulations: 1000,
      exploration_weight: 1.414,
      confidence_threshold: 0.85,
      rollout_horizon_days: 30,
      realtime_budget_ms: 500,
    },
  },
  {
    name: 'Aggressive',
    description: 'Fast decisions with lower confidence threshold',
    settings: {
      max_simulations: 500,
      exploration_weight: 1.0,
      confidence_threshold: 0.75,
      rollout_horizon_days: 14,
      realtime_budget_ms: 250,
    },
  },
];

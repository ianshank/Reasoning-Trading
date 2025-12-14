/**
 * Usage examples for TypeScript type definitions
 *
 * This file demonstrates how to use the types in real React components.
 * It is not part of the actual application - just examples.
 */

import type { FC } from 'react';
import {
  TradingState,
  TradingAction,
  TradingDirection,
  TimeHorizon,
  MarketRegime,
  MCTSResult,
  Portfolio,
  Position,
  APIResponse,
  WSMessage,
  WSMessageType,
  PriceUpdate,
  isSuccessResponse,
  isValidTechnicalIndicators,
  calculateRiskRewardRatio,
  getRiskLevel,
} from './index';

// ==================== Example 1: Trading Dashboard Component ====================

interface TradingDashboardProps {
  state: TradingState;
  portfolio: Portfolio;
}

const TradingDashboard: FC<TradingDashboardProps> = ({ state, portfolio }) => {
  // Type-safe access to all properties
  const { symbol, current_price, technical_indicators, market_regime } = state;
  const { total_value, cash_balance, positions } = portfolio;

  // Type guards ensure data validity
  if (!isValidTechnicalIndicators(technical_indicators)) {
    return <div>Invalid technical indicators</div>;
  }

  // TypeScript knows exact types
  const rsi = technical_indicators.rsi_14 ?? 50;
  const macd = technical_indicators.macd ?? 0;

  return (
    <div>
      <h1>{symbol}</h1>
      <p>Price: ${current_price.toFixed(2)}</p>
      <p>Regime: {market_regime}</p>
      <p>RSI: {rsi.toFixed(1)}</p>
      <p>MACD: {macd.toFixed(3)}</p>
      <p>Portfolio Value: ${total_value.toFixed(2)}</p>
      <p>Cash: ${cash_balance.toFixed(2)}</p>
      <p>Positions: {positions.length}</p>
    </div>
  );
};

// ==================== Example 2: Action Execution ====================

async function executeTradeAction(action: TradingAction): Promise<boolean> {
  // All action properties are type-safe
  const { direction, position_size, stop_loss, time_horizon } = action;

  // Validate action before execution
  if (direction === TradingDirection.HOLD) {
    console.log('No action to execute');
    return false;
  }

  // Calculate risk metrics
  const riskReward = calculateRiskRewardRatio(stop_loss);
  if (riskReward && riskReward < 2) {
    console.warn('Risk/reward ratio below 2:1');
  }

  // Execute trade
  const response = await fetch('/api/trading/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbol: 'AAPL',
      action,
      dry_run: false,
    }),
  });

  const data = await response.json();

  // Type guard for safe access
  if (isSuccessResponse(data)) {
    console.log('Trade executed:', data.data);
    return true;
  } else {
    console.error('Trade failed:', data.error);
    return false;
  }
}

// ==================== Example 3: MCTS Results Display ====================

interface MCTSResultsProps {
  result: MCTSResult;
}

const MCTSResults: FC<MCTSResultsProps> = ({ result }) => {
  const {
    best_action,
    action_distribution,
    total_simulations,
    tree_depth,
    confidence,
    computation_time_ms,
  } = result;

  return (
    <div>
      <h2>MCTS Search Results</h2>
      <div>
        <h3>Best Action</h3>
        <p>Direction: {best_action.direction}</p>
        <p>Size: {(best_action.position_size.size_fraction * 100).toFixed(1)}%</p>
        <p>Stop Loss: {(best_action.stop_loss.stop_loss_pct * 100).toFixed(1)}%</p>
        <p>Confidence: {(confidence * 100).toFixed(1)}%</p>
      </div>

      <div>
        <h3>Search Statistics</h3>
        <p>Simulations: {total_simulations.toLocaleString()}</p>
        <p>Tree Depth: {tree_depth}</p>
        <p>Computation Time: {computation_time_ms.toFixed(0)}ms</p>
      </div>

      <div>
        <h3>Alternative Actions</h3>
        <ul>
          {action_distribution.map((dist, index) => (
            <li key={index}>
              {dist.action.direction} - Visits: {dist.visit_count}, Value:{' '}
              {dist.mean_value.toFixed(3)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

// ==================== Example 4: Position List ====================

interface PositionListProps {
  positions: Position[];
}

const PositionList: FC<PositionListProps> = ({ positions }) => {
  return (
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Side</th>
          <th>Quantity</th>
          <th>Entry Price</th>
          <th>Current Price</th>
          <th>P&L</th>
          <th>P&L %</th>
        </tr>
      </thead>
      <tbody>
        {positions.map((position) => (
          <tr key={position.position_id}>
            <td>{position.symbol}</td>
            <td>{position.side}</td>
            <td>{position.quantity}</td>
            <td>${position.entry_price.toFixed(2)}</td>
            <td>${position.current_price.toFixed(2)}</td>
            <td
              style={{
                color: position.unrealized_pnl >= 0 ? 'green' : 'red',
              }}
            >
              ${position.unrealized_pnl.toFixed(2)}
            </td>
            <td
              style={{
                color: position.unrealized_pnl_pct >= 0 ? 'green' : 'red',
              }}
            >
              {position.unrealized_pnl_pct.toFixed(2)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

// ==================== Example 5: WebSocket Handler ====================

class TradingWebSocket {
  private socket: WebSocket | null = null;
  private onPriceUpdate?: (update: PriceUpdate) => void;

  connect(url: string) {
    this.socket = new WebSocket(url);

    this.socket.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);

        // Type-safe message handling
        switch (message.type) {
          case WSMessageType.PRICE_UPDATE: {
            const priceUpdate = message.data as PriceUpdate;
            this.onPriceUpdate?.(priceUpdate);
            break;
          }

          case WSMessageType.PORTFOLIO_UPDATE: {
            console.log('Portfolio updated:', message.data);
            break;
          }

          case WSMessageType.MCTS_COMPLETED: {
            console.log('MCTS search completed:', message.data);
            break;
          }

          case WSMessageType.RISK_ALERT: {
            console.warn('Risk alert:', message.data);
            break;
          }

          default:
            console.log('Unhandled message type:', message.type);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }

  subscribe(
    channel: string,
    onUpdate: (update: PriceUpdate) => void
  ): void {
    this.onPriceUpdate = onUpdate;
    // Send subscription message
    this.socket?.send(
      JSON.stringify({
        type: WSMessageType.SUBSCRIBE,
        channels: [channel],
      })
    );
  }

  disconnect() {
    this.socket?.close();
  }
}

// ==================== Example 6: Risk Assessment ====================

interface RiskAssessmentProps {
  portfolio: Portfolio;
}

const RiskAssessment: FC<RiskAssessmentProps> = ({ portfolio }) => {
  const { risk_metrics } = portfolio;
  const riskLevel = getRiskLevel(risk_metrics);

  // Color coding based on risk level
  const riskColor = {
    low: 'green',
    medium: 'yellow',
    high: 'orange',
    critical: 'red',
  }[riskLevel];

  return (
    <div>
      <h2>Risk Assessment</h2>
      <p style={{ color: riskColor, fontWeight: 'bold' }}>
        Risk Level: {riskLevel.toUpperCase()}
      </p>

      <div>
        <p>Max Drawdown: {(risk_metrics.max_drawdown * 100).toFixed(2)}%</p>
        <p>Current Drawdown: {(risk_metrics.current_drawdown * 100).toFixed(2)}%</p>
        <p>Sharpe Ratio: {risk_metrics.sharpe_ratio?.toFixed(2) ?? 'N/A'}</p>
        <p>
          Margin Utilization: {(risk_metrics.margin_utilization * 100).toFixed(1)}%
        </p>
        <p>
          Largest Position: {(risk_metrics.largest_position_pct * 100).toFixed(1)}%
        </p>
      </div>
    </div>
  );
};

// ==================== Example 7: Custom Hook for API ====================

import { useState, useEffect } from 'react';

function useTradingDecision(symbol: string) {
  const [decision, setDecision] = useState<TradingAction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDecision() {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/trading/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol,
            use_mcts: true,
            max_simulations: 1000,
          }),
        });

        const data: APIResponse<{ action: TradingAction }> =
          await response.json();

        if (isSuccessResponse(data)) {
          setDecision(data.data.action);
        } else {
          setError(data.error);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    if (symbol) {
      fetchDecision();
    }
  }, [symbol]);

  return { decision, loading, error };
}

// Export examples
export {
  TradingDashboard,
  MCTSResults,
  PositionList,
  RiskAssessment,
  TradingWebSocket,
  useTradingDecision,
  executeTradeAction,
};

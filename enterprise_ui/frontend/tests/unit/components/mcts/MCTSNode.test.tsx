/**
 * MCTSNode Component Tests
 *
 * Tests for the individual MCTS node display component
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MCTSNode } from '../../../../src/components/mcts/MCTSNode';
import { createMCTSNode } from '../../../../src/types/mcts';
import { TradingDirection, OrderType, TimeHorizon } from '../../../../src/types/actions';

/**
 * Create mock MCTS node for testing
 */
function createMockNode(overrides = {}) {
  const node = createMCTSNode('test-node', null, {
    direction: TradingDirection.BUY,
    position_size: { size_fraction: 0.5, kelly_fraction: 0.8 },
    stop_loss: {
      stop_loss_pct: 0.05,
      take_profit_pct: 0.15,
      trailing_stop: false,
      trailing_distance_pct: 0.03,
    },
    time_horizon: TimeHorizon.INTRADAY,
    order_type: OrderType.MARKET,
    limit_price: null,
    confidence: 0.85,
    reasoning: 'Test reasoning for buy action',
  }, null, 0);

  node.visits = 100;
  node.value_sum = 50;
  node.q_value = 0.5;
  node.prior = 0.3;
  node.reflection = 'Test reflection on the action';

  return { ...node, ...overrides };
}

describe('MCTSNode Component', () => {
  it('should render node with action information', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/action: buy/i)).toBeInTheDocument();
    expect(screen.getByText(/buy/i)).toBeInTheDocument();
  });

  it('should display visit statistics', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/visits/i)).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('should display Q-value with correct formatting', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/q-value/i)).toBeInTheDocument();
    expect(screen.getByText('0.500')).toBeInTheDocument();
  });

  it('should display mean value', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/mean value/i)).toBeInTheDocument();
  });

  it('should display UCB score', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/ucb score/i)).toBeInTheDocument();
  });

  it('should display prior probability as progress bar', () => {
    const node = createMockNode();
    const { container } = render(<MCTSNode node={node} />);

    expect(screen.getByText(/prior probability/i)).toBeInTheDocument();
    expect(screen.getByText('30.0%')).toBeInTheDocument();

    const progressBar = container.querySelector('[role="progressbar"]');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '30');
  });

  it('should show best path badge when isOnBestPath is true', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} isOnBestPath={true} />);

    expect(screen.getByText(/best path/i)).toBeInTheDocument();
  });

  it('should show terminal badge when node is terminal', () => {
    const node = createMockNode({ is_terminal: true });
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/terminal/i)).toBeInTheDocument();
  });

  it('should highlight when selected', () => {
    const node = createMockNode();
    const { container } = render(<MCTSNode node={node} isSelected={true} />);

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('ring-2', 'ring-blue-500');
  });

  it('should call onClick when clicked', () => {
    const node = createMockNode();
    const onClick = jest.fn();

    render(<MCTSNode node={node} onClick={onClick} />);

    const card = screen.getByRole('button');
    fireEvent.click(card);

    expect(onClick).toHaveBeenCalledWith('test-node');
  });

  it('should display action details', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/action details/i)).toBeInTheDocument();
    expect(screen.getByText(/position size:/i)).toBeInTheDocument();
    expect(screen.getByText('50.0%')).toBeInTheDocument();
    expect(screen.getByText(/kelly fraction:/i)).toBeInTheDocument();
    expect(screen.getByText('0.80')).toBeInTheDocument();
  });

  it('should expand and collapse reasoning details', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    const toggleButton = screen.getByText(/reasoning & reflection/i);
    expect(toggleButton).toBeInTheDocument();

    // Initially collapsed
    expect(screen.queryByText('Test reasoning for buy action')).not.toBeInTheDocument();

    // Expand
    fireEvent.click(toggleButton);
    expect(screen.getByText('Test reasoning for buy action')).toBeInTheDocument();
    expect(screen.getByText('Test reflection on the action')).toBeInTheDocument();

    // Collapse
    fireEvent.click(toggleButton);
    expect(screen.queryByText('Test reasoning for buy action')).not.toBeInTheDocument();
  });

  it('should display metadata', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/depth: 0/i)).toBeInTheDocument();
    expect(screen.getByText(/children: 0/i)).toBeInTheDocument();
    expect(screen.getByText(/created:/i)).toBeInTheDocument();
  });

  it('should handle root node without action', () => {
    const node = createMCTSNode('root', null, null, null, 0);
    node.visits = 100;
    node.value_sum = 50;
    node.q_value = 0.5;

    render(<MCTSNode node={node} />);

    expect(screen.getByText(/root node/i)).toBeInTheDocument();
  });

  it('should color code Q-values correctly', () => {
    const positiveNode = createMockNode({ q_value: 1.5 });
    const { rerender } = render(<MCTSNode node={positiveNode} />);

    // Positive Q-value should have green color
    let qValueElement = screen.getByText('1.500');
    expect(qValueElement).toHaveClass('text-green-600');

    const negativeNode = createMockNode({ q_value: -1.5 });
    rerender(<MCTSNode node={negativeNode} />);

    // Negative Q-value should have red color
    qValueElement = screen.getByText('-1.500');
    expect(qValueElement).toHaveClass('text-red-600');
  });

  it('should apply custom className', () => {
    const node = createMockNode();
    const { container } = render(
      <MCTSNode node={node} className="custom-class" />
    );

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('custom-class');
  });
});

describe('MCTSNode Accessibility', () => {
  it('should have proper ARIA attributes', () => {
    const node = createMockNode();
    const { container } = render(<MCTSNode node={node} />);

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveAttribute('role', 'button');
    expect(card).toHaveAttribute('tabIndex', '0');
    expect(card).toHaveAttribute('aria-label', 'MCTS node test-node');
  });

  it('should handle keyboard navigation', () => {
    const node = createMockNode();
    const onClick = jest.fn();

    render(<MCTSNode node={node} onClick={onClick} />);

    const card = screen.getByRole('button');

    // Enter key
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onClick).toHaveBeenCalledWith('test-node');

    onClick.mockClear();

    // Space key
    fireEvent.keyDown(card, { key: ' ' });
    expect(onClick).toHaveBeenCalledWith('test-node');
  });

  it('should have proper ARIA expanded state for details', () => {
    const node = createMockNode();
    render(<MCTSNode node={node} />);

    const toggleButton = screen.getByText(/reasoning & reflection/i);

    // Initially collapsed
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

    // Expand
    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
  });

  it('should have proper ARIA attributes for progress bar', () => {
    const node = createMockNode({ prior: 0.75 });
    const { container } = render(<MCTSNode node={node} />);

    const progressBar = container.querySelector('[role="progressbar"]');
    expect(progressBar).toHaveAttribute('aria-valuenow', '75');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    expect(progressBar).toHaveAttribute('aria-label', 'Prior probability');
  });
});

describe('MCTSNode Different Trading Directions', () => {
  it('should display SELL action correctly', () => {
    const node = createMockNode();
    if (node.action) {
      node.action.direction = TradingDirection.SELL;
    }
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/sell/i)).toBeInTheDocument();
  });

  it('should display HOLD action correctly', () => {
    const node = createMockNode();
    if (node.action) {
      node.action.direction = TradingDirection.HOLD;
    }
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/hold/i)).toBeInTheDocument();
  });

  it('should display SHORT action correctly', () => {
    const node = createMockNode();
    if (node.action) {
      node.action.direction = TradingDirection.SHORT;
    }
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/short/i)).toBeInTheDocument();
  });

  it('should display COVER action correctly', () => {
    const node = createMockNode();
    if (node.action) {
      node.action.direction = TradingDirection.COVER;
    }
    render(<MCTSNode node={node} />);

    expect(screen.getByText(/cover/i)).toBeInTheDocument();
  });
});

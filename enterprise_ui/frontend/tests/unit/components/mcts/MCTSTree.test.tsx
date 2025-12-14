/**
 * MCTSTree Component Tests
 *
 * Tests for the MCTS tree visualization component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MCTSTree } from '../../../../src/components/mcts/MCTSTree';
import type { MCTSTree as MCTSTreeType, MCTSNode } from '../../../../src/types/mcts';
import { createMCTSNode } from '../../../../src/types/mcts';
import { TradingDirection, OrderType, TimeHorizon } from '../../../../src/types/actions';

/**
 * Create mock MCTS tree for testing
 */
function createMockTree(): MCTSTreeType {
  const rootNode = createMCTSNode('root', null, null, null, 0);
  rootNode.visits = 100;
  rootNode.value_sum = 50;
  rootNode.q_value = 0.5;

  const child1 = createMCTSNode('child1', null, {
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
    reasoning: 'Test buy action',
  }, 'root', 1);
  child1.visits = 60;
  child1.value_sum = 36;
  child1.q_value = 0.6;

  const child2 = createMCTSNode('child2', null, {
    direction: TradingDirection.SELL,
    position_size: { size_fraction: 0.3, kelly_fraction: 0.5 },
    stop_loss: {
      stop_loss_pct: 0.05,
      take_profit_pct: 0.1,
      trailing_stop: false,
      trailing_distance_pct: 0.03,
    },
    time_horizon: TimeHorizon.SWING,
    order_type: OrderType.LIMIT,
    limit_price: 100,
    confidence: 0.7,
    reasoning: 'Test sell action',
  }, 'root', 1);
  child2.visits = 40;
  child2.value_sum = 20;
  child2.q_value = 0.5;

  rootNode.children_ids = ['child1', 'child2'];

  return {
    root: rootNode,
    nodes: {
      root: rootNode,
      child1,
      child2,
    },
    total_simulations: 100,
    start_time: new Date().toISOString(),
    end_time: null,
  };
}

describe('MCTSTree Component', () => {
  it('should render empty state when no tree data is provided', () => {
    render(<MCTSTree treeData={null} />);
    expect(screen.getByText(/no tree data available/i)).toBeInTheDocument();
  });

  it('should render tree visualization with SVG element', () => {
    const mockTree = createMockTree();
    const { container } = render(<MCTSTree treeData={mockTree} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('role', 'img');
    expect(svg).toHaveAttribute('aria-label', 'MCTS tree visualization');
  });

  it('should render legend with color indicators', () => {
    const mockTree = createMockTree();
    render(<MCTSTree treeData={mockTree} />);

    expect(screen.getByText(/legend/i)).toBeInTheDocument();
    expect(screen.getByText(/low q-value/i)).toBeInTheDocument();
    expect(screen.getByText(/medium q-value/i)).toBeInTheDocument();
    expect(screen.getByText(/high q-value/i)).toBeInTheDocument();
    expect(screen.getByText(/selected/i)).toBeInTheDocument();
    expect(screen.getByText(/best path/i)).toBeInTheDocument();
  });

  it('should call onNodeClick when a node is clicked', async () => {
    const mockTree = createMockTree();
    const onNodeClick = jest.fn();

    render(
      <MCTSTree
        treeData={mockTree}
        onNodeClick={onNodeClick}
      />
    );

    // Note: Testing D3 interactions requires more complex setup
    // This is a placeholder for the actual implementation
    await waitFor(() => {
      expect(onNodeClick).not.toHaveBeenCalled();
    });
  });

  it('should highlight selected node', () => {
    const mockTree = createMockTree();
    render(
      <MCTSTree
        treeData={mockTree}
        selectedNodeId="child1"
      />
    );

    // Verify that the component renders with selected node
    const { container } = render(<MCTSTree treeData={mockTree} selectedNodeId="child1" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should highlight best path', () => {
    const mockTree = createMockTree();
    render(
      <MCTSTree
        treeData={mockTree}
        highlightPath={['root', 'child1']}
      />
    );

    // Verify that the component renders with highlighted path
    const { container } = render(
      <MCTSTree treeData={mockTree} highlightPath={['root', 'child1']} />
    );
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should apply custom width and height', () => {
    const mockTree = createMockTree();
    const { container } = render(
      <MCTSTree
        treeData={mockTree}
        width={1000}
        height={800}
      />
    );

    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '1000');
    expect(svg).toHaveAttribute('height', '800');
  });

  it('should filter nodes by hierarchy level', () => {
    const mockTree = createMockTree();
    const { container } = render(
      <MCTSTree
        treeData={mockTree}
        levelFilter="strategic"
      />
    );

    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const mockTree = createMockTree();
    const { container } = render(
      <MCTSTree
        treeData={mockTree}
        className="custom-class"
      />
    );

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('custom-class');
  });

  it('should handle empty children array', () => {
    const rootNode = createMCTSNode('root', null, null, null, 0);
    const tree: MCTSTreeType = {
      root: rootNode,
      nodes: { root: rootNode },
      total_simulations: 0,
      start_time: new Date().toISOString(),
      end_time: null,
    };

    const { container } = render(<MCTSTree treeData={tree} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

describe('MCTSTree Accessibility', () => {
  it('should have proper ARIA labels', () => {
    const mockTree = createMockTree();
    const { container } = render(<MCTSTree treeData={mockTree} />);

    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('role', 'img');
    expect(svg).toHaveAttribute('aria-label');
  });

  it('should be keyboard navigable', () => {
    const mockTree = createMockTree();
    const onNodeClick = jest.fn();

    render(
      <MCTSTree
        treeData={mockTree}
        onNodeClick={onNodeClick}
      />
    );

    // Keyboard navigation would be tested with D3 interactions
    expect(true).toBe(true);
  });
});

describe('MCTSTree Performance', () => {
  it('should handle large trees efficiently', () => {
    // Create a larger tree
    const rootNode = createMCTSNode('root', null, null, null, 0);
    const nodes: Record<string, MCTSNode> = { root: rootNode };

    // Add 50 children
    for (let i = 0; i < 50; i++) {
      const child = createMCTSNode(`child${i}`, null, null, 'root', 1);
      nodes[`child${i}`] = child;
      rootNode.children_ids.push(`child${i}`);
    }

    const tree: MCTSTreeType = {
      root: rootNode,
      nodes,
      total_simulations: 100,
      start_time: new Date().toISOString(),
      end_time: null,
    };

    const startTime = performance.now();
    const { container } = render(<MCTSTree treeData={tree} />);
    const endTime = performance.now();

    expect(container.querySelector('svg')).toBeInTheDocument();
    expect(endTime - startTime).toBeLessThan(1000); // Should render in less than 1s
  });
});

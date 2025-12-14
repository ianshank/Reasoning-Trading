/**
 * MCTSStats Component Tests
 *
 * Tests for the MCTS statistics panel component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MCTSStats } from '../../../../src/components/mcts/MCTSStats';
import type { MCTSSearchStats } from '../../../../src/components/mcts/hooks/useMCTSWebSocket';
import { MCTSPhase } from '../../../../src/types/mcts';

/**
 * Create mock search statistics for testing
 */
function createMockStats(overrides: Partial<MCTSSearchStats> = {}): MCTSSearchStats {
  return {
    totalSimulations: 100,
    timeElapsed: 5000,
    simulationsPerSecond: 20,
    maxDepth: 5,
    totalNodes: 250,
    bestAction: 'BUY 50%',
    rootValue: 0.5,
    currentPhase: MCTSPhase.SELECTION,
    iteration: 50,
    ...overrides,
  };
}

describe('MCTSStats Component', () => {
  it('should render no statistics message when stats is null', () => {
    render(<MCTSStats stats={null} />);
    expect(screen.getByText(/no statistics available/i)).toBeInTheDocument();
  });

  it('should display total simulations', () => {
    const stats = createMockStats();
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/total simulations/i)).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('should display time elapsed formatted correctly', () => {
    const stats = createMockStats({ timeElapsed: 5000 });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/time elapsed/i)).toBeInTheDocument();
    expect(screen.getByText('5.0s')).toBeInTheDocument();
  });

  it('should format time in milliseconds for short durations', () => {
    const stats = createMockStats({ timeElapsed: 500 });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText('500ms')).toBeInTheDocument();
  });

  it('should format time in minutes and seconds for long durations', () => {
    const stats = createMockStats({ timeElapsed: 125000 }); // 2m 5s
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText('2m 5s')).toBeInTheDocument();
  });

  it('should display simulations per second', () => {
    const stats = createMockStats();
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/simulations\/sec/i)).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('should display max depth', () => {
    const stats = createMockStats();
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/max depth/i)).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('should display total nodes', () => {
    const stats = createMockStats();
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/total nodes/i)).toBeInTheDocument();
    expect(screen.getByText('250')).toBeInTheDocument();
  });

  it('should display root value with correct color coding', () => {
    const positiveStats = createMockStats({ rootValue: 1.5 });
    const { rerender } = render(<MCTSStats stats={positiveStats} />);

    let rootValueElement = screen.getByText('1.500');
    expect(rootValueElement).toHaveClass('text-green-600');

    const negativeStats = createMockStats({ rootValue: -1.5 });
    rerender(<MCTSStats stats={negativeStats} />);

    rootValueElement = screen.getByText('-1.500');
    expect(rootValueElement).toHaveClass('text-red-600');
  });

  it('should display best action when available', () => {
    const stats = createMockStats({ bestAction: 'BUY 75%' });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/best action/i)).toBeInTheDocument();
    expect(screen.getByText('BUY 75%')).toBeInTheDocument();
  });

  it('should show running badge when isSearching is true', () => {
    const stats = createMockStats();
    render(<MCTSStats stats={stats} isSearching={true} />);

    expect(screen.getByText(/running/i)).toBeInTheDocument();
  });

  it('should show current phase badge', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.EXPANSION });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/expansion/i)).toBeInTheDocument();
  });

  it('should display performance metrics', () => {
    const stats = createMockStats({
      iteration: 10,
      timeElapsed: 10000,
      totalNodes: 100,
    });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText(/avg\. time per iteration/i)).toBeInTheDocument();
    expect(screen.getByText(/nodes per iteration/i)).toBeInTheDocument();
    expect(screen.getByText(/tree efficiency/i)).toBeInTheDocument();
  });

  it('should calculate average time per iteration correctly', () => {
    const stats = createMockStats({
      iteration: 10,
      timeElapsed: 10000, // 10 seconds
    });
    render(<MCTSStats stats={stats} />);

    // 10000ms / 10 iterations = 1000ms = 1.0s per iteration
    expect(screen.getByText('1.0s')).toBeInTheDocument();
  });

  it('should calculate nodes per iteration correctly', () => {
    const stats = createMockStats({
      iteration: 10,
      totalNodes: 250,
    });
    render(<MCTSStats stats={stats} />);

    // 250 nodes / 10 iterations = 25 nodes per iteration
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('should calculate tree efficiency correctly', () => {
    const stats = createMockStats({
      totalNodes: 100,
      totalSimulations: 200,
    });
    render(<MCTSStats stats={stats} />);

    // (100 / 200) * 100 = 50.0%
    expect(screen.getByText('50.0%')).toBeInTheDocument();
  });

  it('should display progress indicator when searching', () => {
    const stats = createMockStats({ iteration: 50 });
    const { container } = render(<MCTSStats stats={stats} isSearching={true} />);

    expect(screen.getByText(/iteration progress/i)).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();

    const progressBar = container.querySelector('[role="progressbar"]');
    expect(progressBar).toBeInTheDocument();
  });

  it('should show correct status message when searching', () => {
    const stats = createMockStats();
    render(<MCTSStats stats={stats} isSearching={true} />);

    expect(screen.getByText(/search in progress/i)).toBeInTheDocument();
  });

  it('should show correct status message when search completed', () => {
    const stats = createMockStats({ totalSimulations: 100 });
    render(<MCTSStats stats={stats} isSearching={false} />);

    expect(screen.getByText(/search completed/i)).toBeInTheDocument();
  });

  it('should show ready message when no simulations', () => {
    const stats = createMockStats({ totalSimulations: 0 });
    render(<MCTSStats stats={stats} isSearching={false} />);

    expect(screen.getByText(/ready to start search/i)).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const stats = createMockStats();
    const { container } = render(
      <MCTSStats stats={stats} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('should format large numbers with commas', () => {
    const stats = createMockStats({
      totalSimulations: 10000,
      totalNodes: 50000,
      simulationsPerSecond: 1000,
    });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText('10,000')).toBeInTheDocument();
    expect(screen.getByText('50,000')).toBeInTheDocument();
    expect(screen.getByText('1,000')).toBeInTheDocument();
  });
});

describe('MCTSStats Phase Colors', () => {
  it('should apply correct color for SELECTION phase', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.SELECTION });
    render(<MCTSStats stats={stats} />);

    const badge = screen.getByText(/selection/i);
    expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('should apply correct color for EXPANSION phase', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.EXPANSION });
    render(<MCTSStats stats={stats} />);

    const badge = screen.getByText(/expansion/i);
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('should apply correct color for SIMULATION phase', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.SIMULATION });
    render(<MCTSStats stats={stats} />);

    const badge = screen.getByText(/simulation/i);
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('should apply correct color for BACKPROPAGATION phase', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.BACKPROPAGATION });
    render(<MCTSStats stats={stats} />);

    const badge = screen.getByText(/backpropagation/i);
    expect(badge).toHaveClass('bg-purple-100', 'text-purple-800');
  });

  it('should apply correct color for COMPLETE phase', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.COMPLETE });
    render(<MCTSStats stats={stats} />);

    const badge = screen.getByText(/complete/i);
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('should apply correct color for ERROR phase', () => {
    const stats = createMockStats({ currentPhase: MCTSPhase.ERROR });
    render(<MCTSStats stats={stats} />);

    const badge = screen.getByText(/error/i);
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });
});

describe('MCTSStats Edge Cases', () => {
  it('should handle zero iteration gracefully', () => {
    const stats = createMockStats({ iteration: 0, timeElapsed: 0, totalNodes: 0 });
    render(<MCTSStats stats={stats} />);

    // Should show '-' for calculated metrics
    const dashElements = screen.getAllByText('-');
    expect(dashElements.length).toBeGreaterThan(0);
  });

  it('should handle null best action', () => {
    const stats = createMockStats({ bestAction: null });
    render(<MCTSStats stats={stats} />);

    // Should not display best action section
    expect(screen.queryByText(/selected action/i)).not.toBeInTheDocument();
  });

  it('should handle very small root value', () => {
    const stats = createMockStats({ rootValue: 0.001 });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText('0.001')).toBeInTheDocument();
  });

  it('should handle very large numbers', () => {
    const stats = createMockStats({
      totalSimulations: 1000000,
      totalNodes: 5000000,
    });
    render(<MCTSStats stats={stats} />);

    expect(screen.getByText('1,000,000')).toBeInTheDocument();
    expect(screen.getByText('5,000,000')).toBeInTheDocument();
  });
});

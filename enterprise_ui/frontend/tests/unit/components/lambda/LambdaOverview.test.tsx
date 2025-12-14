import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LambdaOverview } from '../../../../src/components/lambda/LambdaOverview';
import type { LambdaStats } from '../../../../src/components/lambda/hooks/useLambdaStats';

const mockStats: LambdaStats = {
  currentRegime: 'trending_up',
  regimeConfidence: 0.85,
  regimeSince: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
  totalTriggers: 5,
  recentTriggers: [
    {
      previousRegime: 'mean_reverting',
      newRegime: 'trending_up',
      confidence: 0.85,
      action: 'trigger_batch',
      triggeredAt: new Date(Date.now() - 3600000).toISOString(),
      batchJobId: 'batch-123',
      completed: true,
    },
  ],
  batchLayer: {
    isRunning: false,
    pendingJobs: 2,
    runningJobs: 0,
    completedJobs: 10,
    totalResults: 100,
    lastBatchTime: new Date(Date.now() - 86400000).toISOString(), // 24 hours ago
    lastRunDuration: 3600,
    nextScheduledRun: new Date(Date.now() + 3600000).toISOString(), // 1 hour from now
    symbolsProcessed: 50,
    successRate: 0.95,
    avgConfidence: 0.82,
  },
  speedLayer: {
    avgLatencyMs: 15.5,
    p50LatencyMs: 12.0,
    p95LatencyMs: 45.0,
    p99LatencyMs: 85.0,
    maxLatencyMs: 120.0,
    policyNetworkPct: 60.0,
    cacheHitPct: 30.0,
    heuristicPct: 10.0,
    mctsLitePct: 0.0,
    totalDecisions: 10000,
    decisionsPerSecond: 25.5,
    avgConfidence: 0.78,
    errorRate: 0.005,
  },
  servingLayer: {
    backend: 'redis',
    totalEntries: 5000,
    activeEntries: 4500,
    expiredEntries: 500,
    semanticIndexSize: 1000,
    totalAccesses: 50000,
    maxEntries: 10000,
    hitRate: 0.75,
    avgTtl: 3600,
    popularKeys: [
      { key: 'key1', accessCount: 1000 },
      { key: 'key2', accessCount: 800 },
    ],
  },
};

describe('LambdaOverview', () => {
  it('renders without crashing', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('Lambda Architecture Overview')).toBeInTheDocument();
  });

  it('displays current regime correctly', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('trending_up')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 85.0%')).toBeInTheDocument();
  });

  it('displays all three layers in the architecture diagram', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('Batch')).toBeInTheDocument();
    expect(screen.getByText('Serving')).toBeInTheDocument();
    expect(screen.getByText('Speed')).toBeInTheDocument();
  });

  it('displays layer health indicators', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('Batch Layer')).toBeInTheDocument();
    expect(screen.getByText('Speed Layer')).toBeInTheDocument();
    expect(screen.getByText('Serving Layer')).toBeInTheDocument();
  });

  it('displays regime trigger count', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('Regime Changes')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('displays batch layer metrics', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('2')).toBeInTheDocument(); // pending jobs
    expect(screen.getByText('95.0%')).toBeInTheDocument(); // success rate
  });

  it('displays speed layer metrics', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('15.5ms')).toBeInTheDocument(); // avg latency
    expect(screen.getByText('25.5/s')).toBeInTheDocument(); // throughput
  });

  it('displays serving layer metrics', () => {
    render(<LambdaOverview stats={mockStats} />);
    expect(screen.getByText('75.0%')).toBeInTheDocument(); // hit rate
    expect(screen.getByText('4500')).toBeInTheDocument(); // active entries
  });

  it('displays recent regime change information', () => {
    render(<LambdaOverview stats={mockStats} />);
    const regimeChangeText = screen.getByText(/mean_reverting → trending_up/);
    expect(regimeChangeText).toBeInTheDocument();
  });

  it('uses custom regime when provided', () => {
    render(<LambdaOverview stats={mockStats} currentRegime="volatile" />);
    expect(screen.getByText('volatile')).toBeInTheDocument();
  });

  it('has proper accessibility attributes', () => {
    render(<LambdaOverview stats={mockStats} />);
    const overview = screen.getByRole('region', { name: 'Lambda architecture overview' });
    expect(overview).toBeInTheDocument();
  });

  it('correctly determines batch layer status as healthy', () => {
    const healthyStats = { ...mockStats };
    healthyStats.batchLayer.successRate = 0.99;
    render(<LambdaOverview stats={healthyStats} />);
    const batchLayer = screen.getByText('Batch Layer').closest('div');
    expect(batchLayer).toHaveClass('border-green-300', 'dark:border-green-700');
  });

  it('correctly determines speed layer status as degraded when latency is high', () => {
    const degradedStats = { ...mockStats };
    degradedStats.speedLayer.p95LatencyMs = 150;
    render(<LambdaOverview stats={degradedStats} />);
    const speedLayer = screen.getByText('Speed Layer').closest('div');
    expect(speedLayer).toHaveClass('border-yellow-300', 'dark:border-yellow-700');
  });

  it('correctly determines serving layer status as unhealthy when hit rate is low', () => {
    const unhealthyStats = { ...mockStats };
    unhealthyStats.servingLayer.hitRate = 0.4;
    render(<LambdaOverview stats={unhealthyStats} />);
    const servingLayer = screen.getByText('Serving Layer').closest('div');
    expect(servingLayer).toHaveClass('border-red-300', 'dark:border-red-700');
  });

  it('handles zero regime triggers gracefully', () => {
    const noTriggersStats = { ...mockStats, totalTriggers: 0, recentTriggers: [] };
    render(<LambdaOverview stats={noTriggersStats} />);
    expect(screen.getByText('Regime Changes')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});

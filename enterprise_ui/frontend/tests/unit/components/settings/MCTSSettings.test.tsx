import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCTSSettings } from '../../../../src/components/settings/MCTSSettings';
import { MCTSSettings as MCTSSettingsType } from '../../../../src/components/settings/types';

describe('MCTSSettings', () => {
  const mockConfig: MCTSSettingsType = {
    max_simulations: 1000,
    exploration_weight: 1.414,
    rollout_horizon_days: 30,
    confidence_threshold: 0.85,
    realtime_budget_ms: 500,
    progressive_widening_alpha: 0.5,
    discount_factor: 0.99,
  };

  const mockOnChange = vi.fn();
  const mockOnReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state when config is null', () => {
    render(<MCTSSettings config={null} onChange={mockOnChange} onReset={mockOnReset} />);
    expect(screen.getByText(/loading mcts settings/i)).toBeInTheDocument();
  });

  it('renders MCTS configuration settings', () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    expect(screen.getByText('MCTS Configuration')).toBeInTheDocument();
    expect(screen.getByLabelText(/maximum simulations/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/exploration weight/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rollout horizon/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confidence threshold/i)).toBeInTheDocument();
  });

  it('displays current values correctly', () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const maxSimulationsInput = screen.getByLabelText(
      /maximum simulations value/i
    ) as HTMLInputElement;
    expect(maxSimulationsInput.value).toBe('1000');

    const explorationWeightInput = screen.getByLabelText(
      /exploration weight value/i
    ) as HTMLInputElement;
    expect(explorationWeightInput.value).toBe('1.414');
  });

  it('calls onChange when max simulations slider is adjusted', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const slider = screen.getAllByRole('slider', { name: /maximum simulations/i })[0];
    fireEvent.change(slider, { target: { value: '2000' } });

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ max_simulations: 2000 });
    });
  });

  it('calls onChange when exploration weight is modified', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const input = screen.getByLabelText(/exploration weight value/i);
    await user.clear(input);
    await user.type(input, '2.0');

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ exploration_weight: 2.0 });
    });
  });

  it('applies conservative preset when clicked', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const conservativeButton = screen.getByRole('button', { name: /conservative/i });
    await user.click(conservativeButton);

    expect(mockOnChange).toHaveBeenCalledWith({
      max_simulations: 2000,
      exploration_weight: 2.0,
      confidence_threshold: 0.90,
      rollout_horizon_days: 60,
      realtime_budget_ms: 1000,
    });
  });

  it('applies balanced preset when clicked', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const balancedButton = screen.getByRole('button', { name: /balanced/i });
    await user.click(balancedButton);

    expect(mockOnChange).toHaveBeenCalledWith({
      max_simulations: 1000,
      exploration_weight: 1.414,
      confidence_threshold: 0.85,
      rollout_horizon_days: 30,
      realtime_budget_ms: 500,
    });
  });

  it('applies aggressive preset when clicked', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const aggressiveButton = screen.getByRole('button', { name: /aggressive/i });
    await user.click(aggressiveButton);

    expect(mockOnChange).toHaveBeenCalledWith({
      max_simulations: 500,
      exploration_weight: 1.0,
      confidence_threshold: 0.75,
      rollout_horizon_days: 14,
      realtime_budget_ms: 250,
    });
  });

  it('calls onReset when reset button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const resetButton = screen.getByRole('button', { name: /reset.*defaults/i });
    await user.click(resetButton);

    expect(mockOnReset).toHaveBeenCalledTimes(1);
  });

  it('validates max simulations within range', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const input = screen.getByLabelText(/maximum simulations value/i) as HTMLInputElement;

    expect(input.min).toBe('1');
    expect(input.max).toBe('100000');
  });

  it('validates exploration weight within range', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const input = screen.getByLabelText(/exploration weight value/i) as HTMLInputElement;

    expect(input.min).toBe('0');
    expect(input.max).toBe('10');
    expect(input.step).toBe('0.1');
  });

  it('displays info banner about MCTS parameters', () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    expect(screen.getByText(/about mcts parameters/i)).toBeInTheDocument();
    expect(
      screen.getByText(/higher simulation counts provide more accurate results/i)
    ).toBeInTheDocument();
  });

  it('updates all MCTS parameters independently', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const horizonSlider = screen.getAllByRole('slider', {
      name: /rollout horizon/i,
    })[0];
    fireEvent.change(horizonSlider, { target: { value: '60' } });

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ rollout_horizon_days: 60 });
    });

    const confidenceSlider = screen.getAllByRole('slider', {
      name: /confidence threshold/i,
    })[0];
    fireEvent.change(confidenceSlider, { target: { value: '0.90' } });

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ confidence_threshold: 0.9 });
    });
  });

  it('handles discount factor updates', async () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const slider = screen.getAllByRole('slider', { name: /discount factor/i })[0];
    fireEvent.change(slider, { target: { value: '0.95' } });

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ discount_factor: 0.95 });
    });
  });

  it('handles progressive widening alpha updates', async () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const slider = screen.getAllByRole('slider', {
      name: /progressive widening alpha/i,
    })[0];
    fireEvent.change(slider, { target: { value: '0.7' } });

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ progressive_widening_alpha: 0.7 });
    });
  });

  it('handles realtime budget updates', async () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const slider = screen.getAllByRole('slider', { name: /real-time budget/i })[0];
    fireEvent.change(slider, { target: { value: '1000' } });

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith({ realtime_budget_ms: 1000 });
    });
  });

  it('has accessible labels for all inputs', () => {
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    expect(screen.getByLabelText(/maximum simulations value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/exploration weight value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rollout horizon days value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confidence threshold value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/progressive widening alpha value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/discount factor value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/real-time budget value/i)).toBeInTheDocument();
  });

  it('preset buttons have correct aria-pressed state', async () => {
    const user = userEvent.setup();
    render(
      <MCTSSettings config={mockConfig} onChange={mockOnChange} onReset={mockOnReset} />
    );

    const conservativeButton = screen.getByRole('button', { name: /conservative/i });
    expect(conservativeButton).toHaveAttribute('aria-pressed', 'false');

    await user.click(conservativeButton);

    await waitFor(() => {
      expect(conservativeButton).toHaveAttribute('aria-pressed', 'true');
    });
  });
});

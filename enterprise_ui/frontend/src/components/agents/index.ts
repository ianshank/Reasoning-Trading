/**
 * Agent Components Library
 *
 * Components for displaying multi-agent analyst signals, debates,
 * and consensus analysis for trading decisions.
 */

// Main components
export { AnalystRadarChart } from './AnalystRadarChart';
export type { AnalystRadarChartProps } from './AnalystRadarChart';

export { AnalystCard } from './AnalystCard';
export type { AnalystCardProps, AnalystType } from './AnalystCard';

export { AnalystGrid } from './AnalystGrid';
export type { AnalystGridProps } from './AnalystGrid';

export { DebateView } from './DebateView';
export type { DebateViewProps } from './DebateView';

export { ConsensusPanel } from './ConsensusPanel';
export type { ConsensusPanelProps } from './ConsensusPanel';

export { EvidencePacket } from './EvidencePacket';
export type { EvidencePacketProps } from './EvidencePacket';

export { SignalTimeline } from './SignalTimeline';
export type { SignalTimelineProps } from './SignalTimeline';

// Hooks
export { useAgentSignals } from './hooks/useAgentSignals';
export type {
  UseAgentSignalsOptions,
  UseAgentSignalsResult,
  Debate,
  DebateArgument,
  DebateVerdict,
  Consensus,
  EvidenceItem,
  SignalHistory,
  SignalHistoryPoint,
} from './hooks/useAgentSignals';

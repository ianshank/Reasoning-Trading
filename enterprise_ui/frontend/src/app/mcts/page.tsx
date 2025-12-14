import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { MCTSTree } from '@/components/mcts/MCTSTree'
import { MCTSStats } from '@/components/mcts/MCTSStats'
import { MCTSControls } from '@/components/mcts/MCTSControls'
import { MCTSActionDistribution } from '@/components/mcts/MCTSActionDistribution'
import { MCTSTimeline } from '@/components/mcts/MCTSTimeline'
import { MCTSHierarchyView } from '@/components/mcts/MCTSHierarchyView'
import { RefreshCw } from 'lucide-react'

interface MCTSData {
  tree: MCTSNode
  stats: MCTSStatistics
  action_distribution: ActionDistribution[]
  timeline: TimelineEvent[]
  hierarchy_data: HierarchyLevel[]
}

interface MCTSNode {
  id: string
  state: any
  action: string | null
  visits: number
  value: number
  ucb_score: number
  children: MCTSNode[]
  parent_id: string | null
}

interface MCTSStatistics {
  total_simulations: number
  total_nodes: number
  max_depth: number
  avg_depth: number
  exploration_rate: number
  best_action: string
  best_value: number
  confidence: number
  runtime_ms: number
}

interface ActionDistribution {
  action: string
  probability: number
  visits: number
  avg_value: number
}

interface TimelineEvent {
  timestamp: string
  event_type: string
  description: string
  metadata: any
}

interface HierarchyLevel {
  level: string
  description: string
  policy_type: string
  nodes: number
  avg_value: number
}

export default function MCTSPage() {
  const { currentSymbol } = useAppStore()

  const { data: mctsData, isLoading, refetch } = useQuery<MCTSData>({
    queryKey: ['mcts-data', currentSymbol],
    queryFn: () => api.get(`/api/mcts/${currentSymbol}`),
    refetchInterval: 5000,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            MCTS Visualization
          </h1>
          <p className="text-muted-foreground mt-1">
            Monte Carlo Tree Search analysis for {currentSymbol}
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label="Refresh MCTS data"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* MCTS Controls */}
      <MCTSControls symbol={currentSymbol} onUpdate={() => refetch()} />

      {isLoading ? (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="text-center py-12 text-muted-foreground">
            Loading MCTS data...
          </div>
        </div>
      ) : mctsData ? (
        <>
          {/* Stats Overview */}
          <MCTSStats stats={mctsData.stats} />

          {/* Main Visualization Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* MCTS Tree Visualization */}
            <div className="lg:col-span-2">
              <div className="bg-card border border-border rounded-lg p-6">
                <h2 className="text-lg font-semibold mb-4">Search Tree</h2>
                <MCTSTree root={mctsData.tree} />
              </div>
            </div>

            {/* Action Distribution */}
            <div>
              <div className="bg-card border border-border rounded-lg p-6">
                <h2 className="text-lg font-semibold mb-4">
                  Action Distribution
                </h2>
                <MCTSActionDistribution
                  distribution={mctsData.action_distribution}
                />
              </div>
            </div>
          </div>

          {/* Hierarchy View */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">
              Hierarchical MCTS Structure
            </h2>
            <MCTSHierarchyView data={mctsData.hierarchy_data} />
          </div>

          {/* Timeline */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">MCTS Timeline</h2>
            <MCTSTimeline events={mctsData.timeline} />
          </div>
        </>
      ) : (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="text-center py-12 text-muted-foreground">
            No MCTS data available. Run analysis to generate data.
          </div>
        </div>
      )}
    </div>
  )
}

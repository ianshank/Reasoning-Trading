import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'
import { AgentAnalysisView } from '@/components/agents/AgentAnalysisView'
import { TradingDecisionPanel } from '@/components/agents/TradingDecisionPanel'
import { Search, Play, Pause, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

interface AnalysisData {
  symbol: string
  timestamp: string
  reasoning_steps: ReasoningStep[]
  recommendation: {
    action: 'buy' | 'sell' | 'hold'
    confidence: number
    reasoning: string
  }
  market_data: {
    price: number
    volume: number
    change: number
    change_percentage: number
  }
}

interface ReasoningStep {
  step: number
  type: string
  description: string
  result: any
  confidence: number
}

export default function AnalysisPage() {
  const { currentSymbol, setCurrentSymbol } = useAppStore()
  const [searchSymbol, setSearchSymbol] = useState(currentSymbol)
  const [mctsRunning, setMctsRunning] = useState(false)

  const { data: analysis, isLoading, refetch } = useQuery<AnalysisData>({
    queryKey: ['analysis', currentSymbol],
    queryFn: () => api.get(`/api/analysis/${currentSymbol}`),
    refetchInterval: 10000,
  })

  const handleSymbolSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchSymbol.trim()) {
      setCurrentSymbol(searchSymbol.toUpperCase())
    }
  }

  const handleRunMCTS = async () => {
    try {
      setMctsRunning(true)
      await api.post(`/api/mcts/run`, { symbol: currentSymbol })
      refetch()
    } catch (error) {
      console.error('Failed to run MCTS:', error)
    } finally {
      setMctsRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Analysis</h1>
          <p className="text-muted-foreground mt-1">
            AI-powered trading analysis and decision making
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label="Refresh analysis"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Symbol Search & Controls */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Symbol Search */}
          <form onSubmit={handleSymbolSearch} className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="text"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                placeholder="Enter symbol (e.g., AAPL)"
                className="w-full pl-10 pr-4 py-3 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </form>

          {/* MCTS Control */}
          <button
            onClick={handleRunMCTS}
            disabled={mctsRunning}
            className={clsx(
              'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors',
              mctsRunning
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            {mctsRunning ? (
              <>
                <Pause className="w-5 h-5" />
                Running MCTS...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Run MCTS Analysis
              </>
            )}
          </button>
        </div>
      </div>

      {/* Current Symbol Info */}
      {analysis && (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{analysis.symbol}</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Last updated: {new Date(analysis.timestamp).toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold">
                ${analysis.market_data.price.toFixed(2)}
              </p>
              <p
                className={clsx(
                  'text-sm font-medium',
                  analysis.market_data.change >= 0
                    ? 'text-profit'
                    : 'text-loss'
                )}
              >
                {analysis.market_data.change >= 0 ? '+' : ''}
                {analysis.market_data.change.toFixed(2)} (
                {analysis.market_data.change_percentage.toFixed(2)}%)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent Analysis */}
        <div className="lg:col-span-2">
          {isLoading ? (
            <div className="bg-card border border-border rounded-lg p-6">
              <div className="text-center py-12 text-muted-foreground">
                Loading analysis...
              </div>
            </div>
          ) : analysis ? (
            <AgentAnalysisView data={analysis} />
          ) : (
            <div className="bg-card border border-border rounded-lg p-6">
              <div className="text-center py-12 text-muted-foreground">
                No analysis data available
              </div>
            </div>
          )}
        </div>

        {/* Trading Decision Panel */}
        <div>
          {analysis && (
            <TradingDecisionPanel
              recommendation={analysis.recommendation}
              symbol={analysis.symbol}
            />
          )}
        </div>
      </div>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { CurrentRegimeCard } from '@/components/regime/CurrentRegimeCard'
import { RegimeTimeline } from '@/components/regime/RegimeTimeline'
import { RegimeProbabilities } from '@/components/regime/RegimeProbabilities'
import { IndicatorContribution } from '@/components/regime/IndicatorContribution'
import { RefreshCw } from 'lucide-react'

interface RegimeData {
  current: {
    regime: string
    confidence: number
    duration_hours: number
    timestamp: string
  }
  probabilities: {
    regime: string
    probability: number
  }[]
  timeline: {
    timestamp: string
    regime: string
    confidence: number
  }[]
  indicators: {
    name: string
    value: number
    contribution: number
    signal: 'bullish' | 'bearish' | 'neutral'
  }[]
  regime_stats: {
    regime: string
    count: number
    avg_duration_hours: number
    avg_return: number
  }[]
}

export default function RegimePage() {
  const { data: regimeData, isLoading, refetch } = useQuery<RegimeData>({
    queryKey: ['regime-data'],
    queryFn: () => api.get('/api/regime'),
    refetchInterval: 30000,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Market Regime Analysis
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time market regime detection and analysis
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label="Refresh regime data"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {isLoading ? (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="text-center py-12 text-muted-foreground">
            Loading regime data...
          </div>
        </div>
      ) : regimeData ? (
        <>
          {/* Current Regime */}
          <CurrentRegimeCard current={regimeData.current} />

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Regime Probabilities */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">
                Regime Probabilities
              </h2>
              <RegimeProbabilities probabilities={regimeData.probabilities} />
            </div>

            {/* Indicator Contribution */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">
                Indicator Contribution
              </h2>
              <IndicatorContribution indicators={regimeData.indicators} />
            </div>
          </div>

          {/* Regime Timeline */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Regime Timeline</h2>
            <RegimeTimeline timeline={regimeData.timeline} />
          </div>

          {/* Regime Statistics */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Regime Statistics</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                      Regime
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                      Occurrences
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                      Avg Duration (hrs)
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                      Avg Return
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {regimeData.regime_stats.map((stat) => (
                    <tr
                      key={stat.regime}
                      className="border-b border-border last:border-0"
                    >
                      <td className="py-3 px-4">
                        <span className="px-3 py-1 rounded-full text-sm font-medium bg-primary/10 text-primary capitalize">
                          {stat.regime}
                        </span>
                      </td>
                      <td className="text-right py-3 px-4 font-medium">
                        {stat.count}
                      </td>
                      <td className="text-right py-3 px-4 font-medium">
                        {stat.avg_duration_hours.toFixed(1)}
                      </td>
                      <td
                        className={`text-right py-3 px-4 font-medium ${
                          stat.avg_return >= 0 ? 'text-profit' : 'text-loss'
                        }`}
                      >
                        {stat.avg_return >= 0 ? '+' : ''}
                        {stat.avg_return.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="text-center py-12 text-muted-foreground">
            No regime data available
          </div>
        </div>
      )}
    </div>
  )
}

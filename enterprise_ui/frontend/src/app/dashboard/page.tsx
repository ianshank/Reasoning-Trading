import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Briefcase,
  GitBranch,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import clsx from 'clsx'

interface DashboardStats {
  portfolio_value: number
  total_pnl: number
  total_pnl_percentage: number
  open_positions: number
  pending_orders: number
  win_rate: number
  sharpe_ratio: number
  max_drawdown: number
}

interface RecentTrade {
  id: string
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  price: number
  timestamp: string
  pnl?: number
}

interface MarketRegime {
  current: string
  confidence: number
  timestamp: string
}

interface MCTSStatus {
  active: boolean
  total_simulations: number
  best_action: string
  confidence: number
  last_update: string
}

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/api/dashboard/stats'),
    refetchInterval: 5000,
  })

  const { data: recentTrades } = useQuery<RecentTrade[]>({
    queryKey: ['recent-trades'],
    queryFn: () => api.get('/api/trades/recent'),
    refetchInterval: 10000,
  })

  const { data: marketRegime } = useQuery<MarketRegime>({
    queryKey: ['market-regime'],
    queryFn: () => api.get('/api/regime/current'),
    refetchInterval: 30000,
  })

  const { data: mctsStatus } = useQuery<MCTSStatus>({
    queryKey: ['mcts-status'],
    queryFn: () => api.get('/api/mcts/status'),
    refetchInterval: 5000,
  })

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-muted-foreground">
          Loading dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome back! Here's your trading overview.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Portfolio Value */}
        <StatCard
          title="Portfolio Value"
          value={`$${stats?.portfolio_value.toLocaleString() || '0'}`}
          icon={DollarSign}
          trend={stats && stats.total_pnl > 0 ? 'up' : 'down'}
          trendValue={`${stats?.total_pnl_percentage.toFixed(2) || '0'}%`}
        />

        {/* Total P&L */}
        <StatCard
          title="Total P&L"
          value={`$${stats?.total_pnl.toLocaleString() || '0'}`}
          icon={stats && stats.total_pnl >= 0 ? TrendingUp : TrendingDown}
          trend={stats && stats.total_pnl >= 0 ? 'up' : 'down'}
          valueColor={
            stats && stats.total_pnl >= 0 ? 'text-profit' : 'text-loss'
          }
        />

        {/* Open Positions */}
        <StatCard
          title="Open Positions"
          value={stats?.open_positions.toString() || '0'}
          icon={Briefcase}
        />

        {/* Win Rate */}
        <StatCard
          title="Win Rate"
          value={`${stats?.win_rate.toFixed(1) || '0'}%`}
          icon={Activity}
          trend={stats && stats.win_rate > 50 ? 'up' : 'down'}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Trades */}
        <div className="lg:col-span-2">
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Recent Trades</h2>
            <div className="space-y-3">
              {recentTrades && recentTrades.length > 0 ? (
                recentTrades.slice(0, 5).map((trade) => (
                  <div
                    key={trade.id}
                    className="flex items-center justify-between p-3 bg-background rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={clsx(
                          'w-10 h-10 rounded-lg flex items-center justify-center',
                          trade.side === 'buy'
                            ? 'bg-profit/10 text-profit'
                            : 'bg-loss/10 text-loss'
                        )}
                      >
                        {trade.side === 'buy' ? (
                          <ArrowUpRight className="w-5 h-5" />
                        ) : (
                          <ArrowDownRight className="w-5 h-5" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">{trade.symbol}</p>
                        <p className="text-sm text-muted-foreground">
                          {trade.quantity} shares @ ${trade.price.toFixed(2)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {trade.pnl !== undefined && (
                        <p
                          className={clsx(
                            'font-medium',
                            trade.pnl >= 0 ? 'text-profit' : 'text-loss'
                          )}
                        >
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground">
                        {new Date(trade.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No recent trades
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Market Regime */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Market Regime</h2>
            {marketRegime ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Current:</span>
                  <span
                    className={clsx(
                      'px-3 py-1 rounded-full text-sm font-medium',
                      marketRegime.current === 'bull' &&
                        'bg-profit/10 text-profit',
                      marketRegime.current === 'bear' && 'bg-loss/10 text-loss',
                      marketRegime.current === 'sideways' &&
                        'bg-yellow-500/10 text-yellow-500'
                    )}
                  >
                    {marketRegime.current.toUpperCase()}
                  </span>
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-medium">
                      {(marketRegime.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-background rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{ width: `${marketRegime.confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                Loading regime data...
              </div>
            )}
          </div>

          {/* MCTS Status */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <GitBranch className="w-5 h-5" />
              MCTS Status
            </h2>
            {mctsStatus ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span
                    className={clsx(
                      'px-3 py-1 rounded-full text-sm font-medium',
                      mctsStatus.active
                        ? 'bg-profit/10 text-profit'
                        : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {mctsStatus.active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                {mctsStatus.active && (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">
                        Simulations:
                      </span>
                      <span className="font-medium">
                        {mctsStatus.total_simulations.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Best Action:</span>
                      <span className="font-medium">
                        {mctsStatus.best_action}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-muted-foreground">
                          Confidence
                        </span>
                        <span className="font-medium">
                          {(mctsStatus.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-background rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${mctsStatus.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                Loading MCTS data...
              </div>
            )}
          </div>

          {/* Risk Metrics */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Risk Metrics
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Sharpe Ratio:</span>
                <span className="font-medium">
                  {stats?.sharpe_ratio.toFixed(2) || '0.00'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Max Drawdown:</span>
                <span className="font-medium text-loss">
                  {stats?.max_drawdown.toFixed(2) || '0.00'}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  trend?: 'up' | 'down'
  trendValue?: string
  valueColor?: string
}

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendValue,
  valueColor = 'text-foreground',
}: StatCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">{title}</p>
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-primary" />
        </div>
      </div>
      <div>
        <p className={clsx('text-2xl font-bold', valueColor)}>{value}</p>
        {trend && trendValue && (
          <div className="flex items-center gap-1 mt-2">
            {trend === 'up' ? (
              <TrendingUp className="w-4 h-4 text-profit" />
            ) : (
              <TrendingDown className="w-4 h-4 text-loss" />
            )}
            <span
              className={clsx(
                'text-sm font-medium',
                trend === 'up' ? 'text-profit' : 'text-loss'
              )}
            >
              {trendValue}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

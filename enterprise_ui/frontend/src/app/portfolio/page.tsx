import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary'
import { PositionsTable } from '@/components/portfolio/PositionsTable'
import { AllocationChart } from '@/components/charts/AllocationChart'
import { PnLChart } from '@/components/charts/PnLChart'

interface PortfolioData {
  total_value: number
  total_pnl: number
  total_pnl_percentage: number
  cash_balance: number
  positions_value: number
}

interface Position {
  symbol: string
  quantity: number
  avg_price: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_percentage: number
  allocation_percentage: number
}

interface PnLData {
  date: string
  pnl: number
  cumulative_pnl: number
}

export default function PortfolioPage() {
  const { data: portfolio, isLoading: portfolioLoading } =
    useQuery<PortfolioData>({
      queryKey: ['portfolio'],
      queryFn: () => api.get('/api/portfolio'),
      refetchInterval: 5000,
    })

  const { data: positions, isLoading: positionsLoading } = useQuery<
    Position[]
  >({
    queryKey: ['positions'],
    queryFn: () => api.get('/api/portfolio/positions'),
    refetchInterval: 5000,
  })

  const { data: pnlHistory } = useQuery<PnLData[]>({
    queryKey: ['pnl-history'],
    queryFn: () => api.get('/api/portfolio/pnl-history'),
    refetchInterval: 30000,
  })

  const { data: allocation } = useQuery<
    Array<{ name: string; value: number }>
  >({
    queryKey: ['allocation'],
    queryFn: () => api.get('/api/portfolio/allocation'),
    refetchInterval: 30000,
  })

  if (portfolioLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-muted-foreground">
          Loading portfolio...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Portfolio</h1>
        <p className="text-muted-foreground mt-1">
          View and manage your trading positions
        </p>
      </div>

      {/* Portfolio Summary */}
      {portfolio && <PortfolioSummary data={portfolio} />}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* P&L Chart */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">P&L History</h2>
          {pnlHistory && pnlHistory.length > 0 ? (
            <PnLChart data={pnlHistory} />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No P&L data available
            </div>
          )}
        </div>

        {/* Allocation Chart */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Portfolio Allocation</h2>
          {allocation && allocation.length > 0 ? (
            <AllocationChart data={allocation} />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground">
              No allocation data available
            </div>
          )}
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Current Positions</h2>
        {positionsLoading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading positions...
          </div>
        ) : positions && positions.length > 0 ? (
          <PositionsTable positions={positions} />
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            No open positions
          </div>
        )}
      </div>
    </div>
  )
}

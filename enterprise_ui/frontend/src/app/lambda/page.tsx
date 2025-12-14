import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { LambdaOverview } from '@/components/lambda/LambdaOverview'
import { BatchLayerPanel } from '@/components/lambda/BatchLayerPanel'
import { SpeedLayerPanel } from '@/components/lambda/SpeedLayerPanel'
import { ServingLayerPanel } from '@/components/lambda/ServingLayerPanel'
import { RefreshCw, Database, Zap, Globe } from 'lucide-react'

interface LambdaData {
  overview: {
    status: 'healthy' | 'degraded' | 'down'
    batch_layer_status: string
    speed_layer_status: string
    serving_layer_status: string
    last_sync: string
    data_latency_ms: number
  }
  batch_layer: {
    last_run: string
    next_run: string
    records_processed: number
    processing_time_ms: number
    status: string
    datasets: {
      name: string
      size_mb: number
      records: number
      last_updated: string
    }[]
  }
  speed_layer: {
    active_streams: number
    messages_per_second: number
    lag_ms: number
    status: string
    streams: {
      name: string
      throughput: number
      lag_ms: number
      status: string
    }[]
  }
  serving_layer: {
    query_count: number
    avg_query_time_ms: number
    cache_hit_rate: number
    status: string
    endpoints: {
      name: string
      requests_per_min: number
      avg_latency_ms: number
      error_rate: number
    }[]
  }
}

export default function LambdaPage() {
  const { data: lambdaData, isLoading, refetch } = useQuery<LambdaData>({
    queryKey: ['lambda-data'],
    queryFn: () => api.get('/api/lambda'),
    refetchInterval: 5000,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Lambda Architecture
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitor batch, speed, and serving layers
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg hover:bg-accent transition-colors"
          aria-label="Refresh lambda data"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {isLoading ? (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="text-center py-12 text-muted-foreground">
            Loading lambda data...
          </div>
        </div>
      ) : lambdaData ? (
        <>
          {/* Overview */}
          <LambdaOverview overview={lambdaData.overview} />

          {/* Layer Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Batch Layer Status */}
            <div className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Database className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">Batch Layer</h3>
                  <p className="text-sm text-muted-foreground">
                    Historical data processing
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Status:</span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      lambdaData.batch_layer.status === 'running'
                        ? 'bg-profit/10 text-profit'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {lambdaData.batch_layer.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Records:</span>
                  <span className="font-medium">
                    {lambdaData.batch_layer.records_processed.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Speed Layer Status */}
            <div className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">Speed Layer</h3>
                  <p className="text-sm text-muted-foreground">
                    Real-time streaming
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Status:</span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      lambdaData.speed_layer.status === 'running'
                        ? 'bg-profit/10 text-profit'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {lambdaData.speed_layer.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Throughput:</span>
                  <span className="font-medium">
                    {lambdaData.speed_layer.messages_per_second.toFixed(0)}{' '}
                    msg/s
                  </span>
                </div>
              </div>
            </div>

            {/* Serving Layer Status */}
            <div className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Globe className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">Serving Layer</h3>
                  <p className="text-sm text-muted-foreground">
                    Query serving
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Status:</span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      lambdaData.serving_layer.status === 'running'
                        ? 'bg-profit/10 text-profit'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {lambdaData.serving_layer.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Cache Hit:</span>
                  <span className="font-medium">
                    {(lambdaData.serving_layer.cache_hit_rate * 100).toFixed(1)}
                    %
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Detailed Panels */}
          <div className="space-y-6">
            {/* Batch Layer Details */}
            <BatchLayerPanel data={lambdaData.batch_layer} />

            {/* Speed Layer Details */}
            <SpeedLayerPanel data={lambdaData.speed_layer} />

            {/* Serving Layer Details */}
            <ServingLayerPanel data={lambdaData.serving_layer} />
          </div>
        </>
      ) : (
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="text-center py-12 text-muted-foreground">
            No lambda data available
          </div>
        </div>
      )}
    </div>
  )
}

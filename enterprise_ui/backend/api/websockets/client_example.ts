/**
 * TypeScript/JavaScript WebSocket client examples.
 *
 * Demonstrates how to connect to and interact with the WebSocket endpoints
 * from a frontend application.
 */

// ============================================================================
// Type Definitions
// ============================================================================

interface WebSocketMessage {
    type: string;
    data: any;
    timestamp: string;
    metadata?: Record<string, any>;
}

interface MCTSConfig {
    iterations?: number;
    exploration?: number;
    max_depth?: number;
}

interface Position {
    symbol: string;
    quantity: number;
    entry_price: number;
    current_price: number;
    pnl: number;
    pnl_percent: number;
}

// ============================================================================
// Base WebSocket Client
// ============================================================================

class BaseWebSocketClient {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private messageHandlers: Map<string, (data: any) => void> = new Map();

    constructor(
        private url: string,
        private token?: string
    ) {}

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            const wsUrl = this.token
                ? `${this.url}?token=${this.token}`
                : this.url;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log(`Connected to ${this.url}`);
                this.reconnectAttempts = 0;
                resolve();
            };

            this.ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Failed to parse message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket closed');
                this.attemptReconnect();
            };
        });
    }

    private handleMessage(message: WebSocketMessage): void {
        // Handle ping/pong
        if (message.type === 'ping') {
            this.send({ command: 'pong' });
            return;
        }

        // Call registered handler
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
            handler(message.data);
        } else {
            console.log('Unhandled message type:', message.type, message.data);
        }
    }

    on(messageType: string, handler: (data: any) => void): void {
        this.messageHandlers.set(messageType, handler);
    }

    send(data: any): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    private attemptReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);

            setTimeout(() => {
                this.connect().catch((error) => {
                    console.error('Reconnection failed:', error);
                });
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// ============================================================================
// MCTS WebSocket Client
// ============================================================================

class MCTSWebSocketClient extends BaseWebSocketClient {
    constructor(symbol: string, token?: string) {
        super(`ws://localhost:8000/ws/mcts/${symbol}`, token);
    }

    startSearch(config: MCTSConfig): void {
        this.send({
            command: 'start_search',
            config
        });
    }

    stopSearch(searchId: string): void {
        this.send({
            command: 'stop_search',
            search_id: searchId
        });
    }

    updateConfig(searchId: string, config: Partial<MCTSConfig>): void {
        this.send({
            command: 'update_config',
            search_id: searchId,
            config
        });
    }

    getStatus(): void {
        this.send({ command: 'get_status' });
    }
}

// Example usage:
async function exampleMCTSUsage() {
    const client = new MCTSWebSocketClient('AAPL', 'your-token');

    // Set up message handlers
    client.on('connected', (data) => {
        console.log('Connected:', data);

        // Start a search
        client.startSearch({
            iterations: 100,
            exploration: 1.4,
            max_depth: 10
        });
    });

    client.on('search_started', (data) => {
        console.log('Search started:', data.search_id);
    });

    client.on('iteration_update', (data) => {
        console.log(`Progress: ${(data.progress * 100).toFixed(1)}%`);
        console.log(`Best action: ${data.best_action}, Value: ${data.best_value}`);
    });

    client.on('search_completed', (data) => {
        console.log('Search completed!');
        console.log(`Best action: ${data.best_action}`);
        console.log(`Best value: ${data.best_value}`);
        console.log(`Duration: ${data.duration_seconds}s`);
    });

    client.on('error', (data) => {
        console.error('Error:', data.error);
    });

    // Connect
    await client.connect();
}

// ============================================================================
// Market Data WebSocket Client
// ============================================================================

class MarketWebSocketClient extends BaseWebSocketClient {
    constructor(symbol: string, token?: string) {
        super(`ws://localhost:8000/ws/market/${symbol}`, token);
    }

    subscribe(symbols: string[]): void {
        this.send({
            command: 'subscribe',
            symbols
        });
    }

    unsubscribe(symbols: string[]): void {
        this.send({
            command: 'unsubscribe',
            symbols
        });
    }

    getSubscriptions(): void {
        this.send({ command: 'get_subscriptions' });
    }

    getSnapshot(symbol: string): void {
        this.send({
            command: 'get_snapshot',
            symbol
        });
    }
}

// Example usage:
async function exampleMarketUsage() {
    const client = new MarketWebSocketClient('AAPL', 'your-token');

    client.on('connected', (data) => {
        console.log('Connected:', data);

        // Subscribe to additional symbols
        client.subscribe(['MSFT', 'GOOGL']);
    });

    client.on('price_update', (data) => {
        console.log(`${data.symbol}: $${data.price} (Volume: ${data.volume})`);
    });

    client.on('indicator_update', (data) => {
        console.log(`Indicators for ${data.symbol}:`, data.indicators);
    });

    client.on('regime_change', (data) => {
        console.log(`Regime changed from ${data.old_regime} to ${data.new_regime}`);
        console.log(`Confidence: ${(data.confidence * 100).toFixed(1)}%`);
    });

    client.on('ohlcv_update', (data) => {
        console.log(`OHLCV ${data.symbol}:`, {
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            volume: data.volume,
            interval: data.interval
        });
    });

    await client.connect();
}

// ============================================================================
// Trading Decisions WebSocket Client
// ============================================================================

class DecisionWebSocketClient extends BaseWebSocketClient {
    constructor(token?: string) {
        super('ws://localhost:8000/ws/decisions', token);
    }

    getRecent(limit: number = 20): void {
        this.send({
            command: 'get_recent',
            limit
        });
    }

    getDecision(decisionId: string): void {
        this.send({
            command: 'get_decision',
            decision_id: decisionId
        });
    }

    filterBySymbol(symbol: string): void {
        this.send({
            command: 'filter_by_symbol',
            symbol
        });
    }
}

// Example usage:
async function exampleDecisionUsage() {
    const client = new DecisionWebSocketClient('your-token');

    client.on('connected', (data) => {
        console.log('Connected:', data);
        console.log('Recent decisions:', data.recent_decisions);
    });

    client.on('trading_decision', (data) => {
        console.log('New trading decision:');
        console.log(`  Symbol: ${data.symbol}`);
        console.log(`  Action: ${data.action}`);
        console.log(`  Quantity: ${data.quantity}`);
        console.log(`  Price: ${data.price}`);
        console.log(`  Rationale: ${data.rationale}`);
        console.log(`  Confidence: ${(data.confidence * 100).toFixed(1)}%`);
    });

    client.on('trade_execution', (data) => {
        console.log('Trade execution:');
        console.log(`  Status: ${data.status}`);
        console.log(`  Symbol: ${data.symbol}`);
        console.log(`  Action: ${data.action}`);
        console.log(`  Price: ${data.price}`);
    });

    client.on('regime_triggered_decision', (data) => {
        console.log('Regime-triggered decision:');
        console.log(`  ${data.old_regime} → ${data.new_regime}`);
        console.log(`  Action: ${data.action}`);
        console.log(`  Rationale: ${data.rationale}`);
    });

    await client.connect();
}

// ============================================================================
// Portfolio WebSocket Client
// ============================================================================

class PortfolioWebSocketClient extends BaseWebSocketClient {
    constructor(token: string) {
        super('ws://localhost:8000/ws/portfolio', token);
    }

    getPortfolio(): void {
        this.send({ command: 'get_portfolio' });
    }

    getPositions(): void {
        this.send({ command: 'get_positions' });
    }

    getPerformance(): void {
        this.send({ command: 'get_performance' });
    }

    getRiskMetrics(): void {
        this.send({ command: 'get_risk_metrics' });
    }
}

// Example usage:
async function examplePortfolioUsage() {
    const client = new PortfolioWebSocketClient('your-token');

    client.on('connected', (data) => {
        console.log('Connected:', data);
        console.log('Current portfolio:', data.current_portfolio);
    });

    client.on('position_update', (data: Position) => {
        console.log(`Position update for ${data.symbol}:`);
        console.log(`  Quantity: ${data.quantity}`);
        console.log(`  Entry: $${data.entry_price}`);
        console.log(`  Current: $${data.current_price}`);
        console.log(`  P&L: $${data.pnl} (${data.pnl_percent.toFixed(2)}%)`);
    });

    client.on('pnl_update', (data) => {
        console.log('P&L Update:');
        console.log(`  Total: $${data.total_pnl}`);
        console.log(`  Daily: $${data.daily_pnl}`);
        console.log(`  Unrealized: $${data.unrealized_pnl}`);
        console.log(`  Realized: $${data.realized_pnl}`);
    });

    client.on('risk_alert', (data) => {
        console.warn(`RISK ALERT [${data.severity}]:`, data.message);
        console.warn('Details:', data.details);
    });

    client.on('portfolio_summary', (data) => {
        console.log('Portfolio Summary:');
        console.log(`  Total Value: $${data.total_value}`);
        console.log(`  Cash: $${data.cash}`);
        console.log(`  Positions: $${data.positions_value}`);
        console.log(`  # Positions: ${data.num_positions}`);
    });

    await client.connect();
}

// ============================================================================
// React Hook Example
// ============================================================================

/**
 * React hook for MCTS WebSocket connection.
 */
function useMCTSWebSocket(symbol: string, token?: string) {
    const [searchProgress, setSearchProgress] = React.useState(0);
    const [bestAction, setBestAction] = React.useState<string | null>(null);
    const [isConnected, setIsConnected] = React.useState(false);
    const clientRef = React.useRef<MCTSWebSocketClient | null>(null);

    React.useEffect(() => {
        const client = new MCTSWebSocketClient(symbol, token);

        client.on('connected', () => {
            setIsConnected(true);
        });

        client.on('iteration_update', (data) => {
            setSearchProgress(data.progress);
            setBestAction(data.best_action);
        });

        client.on('search_completed', (data) => {
            setBestAction(data.best_action);
            setSearchProgress(1);
        });

        client.connect();
        clientRef.current = client;

        return () => {
            client.disconnect();
        };
    }, [symbol, token]);

    const startSearch = (config: MCTSConfig) => {
        clientRef.current?.startSearch(config);
    };

    return {
        isConnected,
        searchProgress,
        bestAction,
        startSearch
    };
}

// ============================================================================
// Multi-Client Manager
// ============================================================================

/**
 * Manages multiple WebSocket connections.
 */
class WebSocketManager {
    private clients: Map<string, BaseWebSocketClient> = new Map();

    async connectMCTS(symbol: string, token?: string): Promise<MCTSWebSocketClient> {
        const key = `mcts:${symbol}`;
        if (this.clients.has(key)) {
            return this.clients.get(key) as MCTSWebSocketClient;
        }

        const client = new MCTSWebSocketClient(symbol, token);
        await client.connect();
        this.clients.set(key, client);
        return client;
    }

    async connectMarket(symbol: string, token?: string): Promise<MarketWebSocketClient> {
        const key = `market:${symbol}`;
        if (this.clients.has(key)) {
            return this.clients.get(key) as MarketWebSocketClient;
        }

        const client = new MarketWebSocketClient(symbol, token);
        await client.connect();
        this.clients.set(key, client);
        return client;
    }

    async connectDecisions(token?: string): Promise<DecisionWebSocketClient> {
        const key = 'decisions';
        if (this.clients.has(key)) {
            return this.clients.get(key) as DecisionWebSocketClient;
        }

        const client = new DecisionWebSocketClient(token);
        await client.connect();
        this.clients.set(key, client);
        return client;
    }

    async connectPortfolio(token: string): Promise<PortfolioWebSocketClient> {
        const key = 'portfolio';
        if (this.clients.has(key)) {
            return this.clients.get(key) as PortfolioWebSocketClient;
        }

        const client = new PortfolioWebSocketClient(token);
        await client.connect();
        this.clients.set(key, client);
        return client;
    }

    disconnect(key: string): void {
        const client = this.clients.get(key);
        if (client) {
            client.disconnect();
            this.clients.delete(key);
        }
    }

    disconnectAll(): void {
        this.clients.forEach((client) => client.disconnect());
        this.clients.clear();
    }
}

// Example usage:
async function exampleMultiClientUsage() {
    const manager = new WebSocketManager();
    const token = 'your-jwt-token';

    // Connect to multiple endpoints
    const mctsClient = await manager.connectMCTS('AAPL', token);
    const marketClient = await manager.connectMarket('AAPL', token);
    const decisionsClient = await manager.connectDecisions(token);
    const portfolioClient = await manager.connectPortfolio(token);

    // Set up handlers
    mctsClient.on('iteration_update', (data) => {
        console.log('MCTS Progress:', data.progress);
    });

    marketClient.on('price_update', (data) => {
        console.log('Price:', data.price);
    });

    // Clean up on exit
    window.addEventListener('beforeunload', () => {
        manager.disconnectAll();
    });
}

// Export classes for use in your application
export {
    BaseWebSocketClient,
    MCTSWebSocketClient,
    MarketWebSocketClient,
    DecisionWebSocketClient,
    PortfolioWebSocketClient,
    WebSocketManager,
    useMCTSWebSocket
};

"""
Command-line interface for Reasoning Trading.

Provides CLI commands for running trading analysis, batch planning,
and real-time decision making.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

import structlog

from reasoning_trading.config import Settings, TradingMode, get_settings


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            (
                structlog.processors.JSONRenderer()
                if json_format
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger(__name__)


async def run_analysis(symbol: str, date: str | None, settings: Settings) -> int:
    """Run single symbol analysis."""
    from reasoning_trading.workflow.graph import build_trading_mcts_graph

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    logger.info("Starting analysis", symbol=symbol, date=date)

    graph = build_trading_mcts_graph(settings)

    try:
        result = await graph.run(symbol, date)

        if result.best_action:
            print(f"\n{'='*60}")
            print(f"Analysis Result for {symbol}")
            print(f"{'='*60}")
            print(f"Direction: {result.best_action.direction.value.upper()}")
            print(f"Position Size: {result.best_action.position_size.size_fraction:.1%}")
            print(f"Stop Loss: {result.best_action.stop_loss.stop_loss_pct:.1%}")
            print(f"Confidence: {result.action_confidence:.1%}")
            print(f"\nReasoning:\n{result.action_reasoning}")
            print(f"{'='*60}\n")
            return 0
        else:
            print(f"No action recommended for {symbol}")
            return 1

    except Exception as e:
        logger.error("Analysis failed", error=str(e))
        return 1
    finally:
        await graph.cleanup()


async def run_batch_planning(symbols: list[str], settings: Settings) -> int:
    """Run batch MCTS planning for multiple symbols."""
    from reasoning_trading.workflow.hybrid import HybridTradingArchitecture

    logger.info("Starting batch planning", symbols=symbols)

    hybrid = HybridTradingArchitecture(settings=settings)

    try:
        await hybrid.initialize()

        def progress(symbol: str, current: int, total: int) -> None:
            print(f"[{current}/{total}] Completed {symbol}")

        results = await hybrid.nightly_planning(symbols, progress_callback=progress)

        print(f"\n{'='*60}")
        print("Batch Planning Results")
        print(f"{'='*60}")
        for symbol, result in results.items():
            if result.best_action:
                print(f"{symbol}: {result.best_action.direction.value.upper()} "
                      f"(confidence: {result.best_visits / max(result.total_simulations, 1):.1%})")
            else:
                print(f"{symbol}: HOLD (no strong signal)")
        print(f"{'='*60}\n")

        return 0

    except Exception as e:
        logger.error("Batch planning failed", error=str(e))
        return 1
    finally:
        await hybrid.cleanup()


async def run_realtime(symbol: str, settings: Settings) -> int:
    """Run real-time decision making."""
    from reasoning_trading.workflow.hybrid import HybridTradingArchitecture

    logger.info("Starting real-time analysis", symbol=symbol)

    hybrid = HybridTradingArchitecture(settings=settings)

    try:
        await hybrid.initialize()

        action = await hybrid.realtime_decision(symbol)

        print(f"\n{'='*60}")
        print(f"Real-time Decision for {symbol}")
        print(f"{'='*60}")
        print(f"Direction: {action.direction.value.upper()}")
        print(f"Position Size: {action.position_size.size_fraction:.1%}")
        print(f"Confidence: {action.confidence:.1%}")
        print(f"Reasoning: {action.reasoning}")
        print(f"{'='*60}\n")

        return 0

    except Exception as e:
        logger.error("Real-time analysis failed", error=str(e))
        return 1
    finally:
        await hybrid.cleanup()


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="reasoning-trading",
        description="MCTS-Enhanced Multi-Agent Trading Framework",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output logs in JSON format",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a symbol using MCTS",
    )
    analyze_parser.add_argument(
        "symbol",
        help="Trading symbol (e.g., AAPL, NVDA)",
    )
    analyze_parser.add_argument(
        "-d", "--date",
        help="Analysis date (YYYY-MM-DD, defaults to today)",
    )

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Run batch planning for multiple symbols",
    )
    batch_parser.add_argument(
        "symbols",
        nargs="+",
        help="Symbols to analyze",
    )

    # Realtime command
    realtime_parser = subparsers.add_parser(
        "realtime",
        help="Make real-time trading decision",
    )
    realtime_parser.add_argument(
        "symbol",
        help="Trading symbol",
    )

    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Show current configuration",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level, json_format=args.json_logs)

    # Load settings
    settings = get_settings()

    if args.command == "analyze":
        return asyncio.run(run_analysis(args.symbol, args.date, settings))

    elif args.command == "batch":
        return asyncio.run(run_batch_planning(args.symbols, settings))

    elif args.command == "realtime":
        return asyncio.run(run_realtime(args.symbol, settings))

    elif args.command == "config":
        api_keys = settings.validate_api_keys()
        print("\nConfiguration Status:")
        print(f"  Trading Mode: {settings.trading.trading_mode.value}")
        print(f"  MCTS Simulations: {settings.mcts.max_simulations}")
        print(f"  Rollout Horizon: {settings.mcts.rollout_horizon_days} days")
        print(f"  Risk Profile: {settings.risk.default_risk_profile.value}")
        print(f"\nAPI Keys Configured:")
        for key, configured in api_keys.items():
            status = "✓" if configured else "✗"
            print(f"  {status} {key}")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

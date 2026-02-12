"""
Trade Executor
Executes trades with dry-run and live modes
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from logger_setup import get_logger
from kalshi_client import KalshiClient
from allocator import PositionAllocation

logger = get_logger("executor")


@dataclass
class TradeExecution:
    """
    Record of a trade execution

    Attributes:
        ticker: Market ticker
        side: "YES" or "NO"
        num_contracts: Number of contracts
        entry_price: Price paid per contract
        total_cost: Total cost of trade
        timestamp: When trade was executed
        execution_type: "dry-run" or "live"
        order_id: Order ID from API (None for dry-run)
        status: "success", "failed", or "pending"
        error_message: Error message if failed
    """
    ticker: str
    side: str
    num_contracts: int
    entry_price: float
    total_cost: float
    timestamp: datetime
    execution_type: str
    order_id: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"TradeExecution("
            f"ticker={self.ticker}, "
            f"side={self.side}, "
            f"contracts={self.num_contracts}, "
            f"price=${self.entry_price:.2f}, "
            f"total=${self.total_cost:.2f}, "
            f"status={self.status})"
        )


class Executor:
    """
    Executes trades on Kalshi

    Two modes:
    - Dry-run: Simulates trades without API calls (default)
    - Live: Actually places orders on Kalshi

    Order Type:
    - Uses LIMIT orders (not market orders)
    - Limit orders qualify for MAKER fees (lower than taker fees)
    - Kalshi maker fees: ~3.5% vs taker fees: ~7%
    - Limit price set at current ask to fill immediately

    Safety features:
    - Requires explicit live mode activation
    - Validates orders before submission
    - Tracks execution history
    - Handles API errors gracefully
    - Slippage protection (max 2%)
    """

    def __init__(self, client: KalshiClient, config: Dict[str, Any], dry_run: bool = True):
        self.client = client
        self.config = config
        self.dry_run = dry_run

        # Execution history
        self.executions: List[TradeExecution] = []

        # Safety limits
        self.max_slippage_pct = config.get('max_slippage_pct', 0.02)  # 2% max slippage

        mode = "DRY-RUN" if dry_run else "🔴 LIVE"
        logger.info(f"Executor initialized in {mode} mode")
        logger.info(f"  Max slippage: {self.max_slippage_pct * 100:.1f}%")

    def execute_allocations(self, allocations: List[PositionAllocation]) -> List[TradeExecution]:
        """
        Execute a batch of position allocations

        Args:
            allocations: List of allocations to execute

        Returns:
            List of trade executions
        """
        if not allocations:
            logger.info("No allocations to execute")
            return []

        mode = "dry-run" if self.dry_run else "live"
        logger.info(f"📤 Executing {len(allocations)} positions in {mode} mode...")

        executions = []

        for alloc in allocations:
            try:
                execution = self._execute_single(alloc)
                executions.append(execution)

                if execution.status == "success":
                    logger.info(f"  ✅ {execution.ticker} - {execution.num_contracts} contracts @ ${execution.entry_price:.2f}")
                else:
                    logger.warning(f"  ❌ {execution.ticker} - {execution.error_message}")

            except Exception as e:
                logger.error(f"  ❌ {alloc.opportunity.market.ticker} - Unexpected error: {e}")
                executions.append(TradeExecution(
                    ticker=alloc.opportunity.market.ticker,
                    side=alloc.opportunity.side,
                    num_contracts=alloc.num_contracts,
                    entry_price=alloc.opportunity.entry_price,
                    total_cost=alloc.position_size_dollars,
                    timestamp=datetime.utcnow(),
                    execution_type="dry-run" if self.dry_run else "live",
                    status="failed",
                    error_message=str(e)
                ))

        # Store executions
        self.executions.extend(executions)

        # Summary
        successful = sum(1 for e in executions if e.status == "success")
        failed = sum(1 for e in executions if e.status == "failed")

        logger.info(f"✅ Execution complete: {successful} successful, {failed} failed")

        return executions

    def _execute_single(self, allocation: PositionAllocation) -> TradeExecution:
        """
        Execute a single position allocation

        Args:
            allocation: Position to execute

        Returns:
            TradeExecution record
        """
        opp = allocation.opportunity
        ticker = opp.market.ticker
        side = opp.side
        num_contracts = allocation.num_contracts
        entry_price = opp.entry_price

        if self.dry_run:
            # Dry-run mode - simulate execution
            return TradeExecution(
                ticker=ticker,
                side=side,
                num_contracts=num_contracts,
                entry_price=entry_price,
                total_cost=allocation.position_size_dollars,
                timestamp=datetime.utcnow(),
                execution_type="dry-run",
                order_id=None,
                status="success",
                error_message=None
            )

        # Live mode - actually place order
        try:
            # Refresh market data to check for slippage
            market_data = self.client.get_market(ticker)
            if not market_data:
                raise Exception("Failed to fetch current market data")

            # Check current price
            current_price = (market_data.get('yes_ask', 0) / 100.0 if side == "YES"
                           else market_data.get('no_ask', 0) / 100.0)

            # Check slippage
            slippage = abs(current_price - entry_price) / entry_price
            if slippage > self.max_slippage_pct:
                raise Exception(f"Slippage too high: {slippage * 100:.1f}% > {self.max_slippage_pct * 100:.1f}%")

            # Place LIMIT order (not market order)
            # Limit orders get MAKER fees (~3.5%) instead of TAKER fees (~7%)
            # We set limit price at current ask to fill immediately while qualifying for maker fees
            order_response = self.client.place_order(
                ticker=ticker,
                side=side,
                num_contracts=num_contracts,
                limit_price=int(current_price * 100)  # Convert to cents
            )

            if not order_response:
                raise Exception("Order placement failed - no response")

            order_id = order_response.get('order', {}).get('order_id')
            if not order_id:
                raise Exception("Order placement failed - no order ID")

            return TradeExecution(
                ticker=ticker,
                side=side,
                num_contracts=num_contracts,
                entry_price=current_price,
                total_cost=num_contracts * current_price,
                timestamp=datetime.utcnow(),
                execution_type="live",
                order_id=order_id,
                status="success",
                error_message=None
            )

        except Exception as e:
            return TradeExecution(
                ticker=ticker,
                side=side,
                num_contracts=num_contracts,
                entry_price=entry_price,
                total_cost=allocation.position_size_dollars,
                timestamp=datetime.utcnow(),
                execution_type="live",
                order_id=None,
                status="failed",
                error_message=str(e)
            )

    def set_mode(self, dry_run: bool) -> None:
        """
        Switch between dry-run and live mode

        Args:
            dry_run: True for dry-run, False for live
        """
        old_mode = "dry-run" if self.dry_run else "live"
        new_mode = "dry-run" if dry_run else "live"

        if old_mode == new_mode:
            logger.info(f"Already in {new_mode} mode")
            return

        self.dry_run = dry_run

        if not dry_run:
            logger.warning("⚠️  SWITCHING TO LIVE MODE - REAL MONEY AT RISK!")
        else:
            logger.info("✅ Switched to dry-run mode (safe)")

    def get_execution_history(self) -> List[TradeExecution]:
        """
        Get history of all executions

        Returns:
            List of trade executions
        """
        return self.executions.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics

        Returns:
            Dictionary of statistics
        """
        if not self.executions:
            return {
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'total_contracts': 0,
                'total_cost': 0,
                'dry_run_count': 0,
                'live_count': 0
            }

        successful = [e for e in self.executions if e.status == "success"]
        failed = [e for e in self.executions if e.status == "failed"]
        dry_run = [e for e in self.executions if e.execution_type == "dry-run"]
        live = [e for e in self.executions if e.execution_type == "live"]

        return {
            'total_executions': len(self.executions),
            'successful': len(successful),
            'failed': len(failed),
            'total_contracts': sum(e.num_contracts for e in successful),
            'total_cost': sum(e.total_cost for e in successful),
            'dry_run_count': len(dry_run),
            'live_count': len(live),
            'success_rate': len(successful) / len(self.executions) * 100 if self.executions else 0
        }

"""
Portfolio Tracker
Tracks positions, settlements, and P&L
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from logger_setup import get_logger
from kalshi_client import KalshiClient
from executor import TradeExecution

logger = get_logger("tracker")


@dataclass
class Position:
    """
    Active position in portfolio

    Attributes:
        ticker: Market ticker
        side: "YES" or "NO"
        num_contracts: Number of contracts held
        entry_price: Average entry price
        total_cost: Total cost basis
        entry_time: When position was opened
        market_title: Human-readable market title
        settlement_time: When market settles
        current_value: Current mark-to-market value
        unrealized_pnl: Unrealized profit/loss
    """
    ticker: str
    side: str
    num_contracts: int
    entry_price: float
    total_cost: float
    entry_time: datetime
    market_title: str = ""
    settlement_time: Optional[datetime] = None
    current_value: float = 0.0
    unrealized_pnl: float = 0.0

    def update_value(self, current_price: float) -> None:
        """Update current value and unrealized P&L"""
        self.current_value = self.num_contracts * current_price
        self.unrealized_pnl = self.current_value - self.total_cost


@dataclass
class SettledPosition:
    """
    Settled position (win or loss)

    Attributes:
        ticker: Market ticker
        side: "YES" or "NO"
        num_contracts: Number of contracts
        entry_price: Entry price paid
        total_cost: Total cost basis
        settlement_value: Final settlement value
        realized_pnl: Realized profit/loss
        entry_time: When position was opened
        settlement_time: When position was settled
        won: True if position won
    """
    ticker: str
    side: str
    num_contracts: int
    entry_price: float
    total_cost: float
    settlement_value: float
    realized_pnl: float
    entry_time: datetime
    settlement_time: datetime
    won: bool


class Tracker:
    """
    Tracks portfolio, positions, and performance

    Responsibilities:
    - Track active positions
    - Monitor settlements
    - Calculate P&L
    - Generate performance reports
    """

    def __init__(self, client: KalshiClient, dry_run: bool = True):
        self.client = client
        self.dry_run = dry_run

        # Portfolio state
        self.positions: Dict[str, Position] = {}  # ticker -> Position
        self.settled_positions: List[SettledPosition] = []

        # Performance tracking
        self.starting_balance: float = 0.0
        self.current_balance: float = 0.0

        mode = "DRY-RUN" if dry_run else "LIVE"
        logger.info(f"Tracker initialized in {mode} mode")

    def initialize_balance(self, balance: float) -> None:
        """
        Set starting balance

        Args:
            balance: Starting balance amount
        """
        self.starting_balance = balance
        self.current_balance = balance
        logger.info(f"💰 Balance initialized: ${balance:.2f}")

    def add_executions(self, executions: List[TradeExecution]) -> None:
        """
        Add new executions to portfolio

        Args:
            executions: List of trade executions to add
        """
        for execution in executions:
            if execution.status != "success":
                logger.debug(f"Skipping failed execution: {execution.ticker}")
                continue

            self._add_position(execution)

        logger.info(f"📊 Added {len(executions)} executions to portfolio")
        logger.info(f"   Active positions: {len(self.positions)}")

    def _add_position(self, execution: TradeExecution) -> None:
        """
        Add a single execution to portfolio

        Args:
            execution: Trade execution to add
        """
        ticker = execution.ticker

        if ticker in self.positions:
            # Add to existing position (average up/down)
            existing = self.positions[ticker]

            # Make sure sides match
            if existing.side != execution.side:
                logger.warning(f"⚠️  {ticker}: Conflicting sides {existing.side} vs {execution.side}")
                return

            # Calculate new average price
            total_contracts = existing.num_contracts + execution.num_contracts
            total_cost = existing.total_cost + execution.total_cost
            avg_price = total_cost / total_contracts if total_contracts > 0 else 0

            existing.num_contracts = total_contracts
            existing.total_cost = total_cost
            existing.entry_price = avg_price

            logger.debug(f"  Added to {ticker}: now {total_contracts} contracts @ ${avg_price:.2f}")

        else:
            # New position
            position = Position(
                ticker=ticker,
                side=execution.side,
                num_contracts=execution.num_contracts,
                entry_price=execution.entry_price,
                total_cost=execution.total_cost,
                entry_time=execution.timestamp
            )
            self.positions[ticker] = position

            logger.debug(f"  Opened {ticker}: {execution.num_contracts} contracts @ ${execution.entry_price:.2f}")

    def update_positions(self) -> None:
        """
        Update all positions with current prices and check for settlements
        """
        if not self.positions:
            logger.debug("No positions to update")
            return

        logger.debug(f"📊 Updating {len(self.positions)} positions...")

        tickers_to_settle = []

        for ticker, position in self.positions.items():
            try:
                # Get current market data
                market_data = self.client.get_market(ticker)

                if not market_data:
                    logger.warning(f"⚠️  {ticker}: Failed to fetch market data")
                    continue

                # Update market info
                position.market_title = market_data.get('title', '')

                # Check if market settled
                status = market_data.get('status', 'open')
                if status == 'settled' or status == 'closed':
                    tickers_to_settle.append(ticker)
                    continue

                # Update current value
                if position.side == "YES":
                    current_price = market_data.get('yes_bid', 0) / 100.0
                else:
                    current_price = market_data.get('no_bid', 0) / 100.0

                position.update_value(current_price)

            except Exception as e:
                logger.debug(f"  Error updating {ticker}: {e}")

        # Settle positions
        for ticker in tickers_to_settle:
            self._settle_position(ticker)

        logger.debug("✅ Position update complete")

    def _settle_position(self, ticker: str) -> None:
        """
        Settle a position

        Args:
            ticker: Ticker to settle
        """
        if ticker not in self.positions:
            return

        position = self.positions[ticker]

        try:
            # Get market data to determine outcome
            market_data = self.client.get_market(ticker)
            if not market_data:
                logger.warning(f"⚠️  {ticker}: Cannot settle - no market data")
                return

            # Determine if position won
            result = market_data.get('result', '')
            won = (position.side == "YES" and result == "yes") or (position.side == "NO" and result == "no")

            # Calculate settlement value
            if won:
                settlement_value = position.num_contracts * 1.0  # $1 per contract
            else:
                settlement_value = 0.0

            realized_pnl = settlement_value - position.total_cost

            # Create settled position record
            settled = SettledPosition(
                ticker=ticker,
                side=position.side,
                num_contracts=position.num_contracts,
                entry_price=position.entry_price,
                total_cost=position.total_cost,
                settlement_value=settlement_value,
                realized_pnl=realized_pnl,
                entry_time=position.entry_time,
                settlement_time=datetime.utcnow(),
                won=won
            )

            self.settled_positions.append(settled)

            # Update balance
            self.current_balance += realized_pnl

            # Remove from active positions
            del self.positions[ticker]

            win_loss = "WON" if won else "LOST"
            logger.info(f"🏁 {ticker} settled: {win_loss} - P&L: ${realized_pnl:+.2f}")

        except Exception as e:
            logger.error(f"❌ Error settling {ticker}: {e}")

    def get_portfolio_value(self) -> float:
        """
        Get total portfolio value (cash + positions)

        Returns:
            Total portfolio value
        """
        cash = self.current_balance
        position_value = sum(p.current_value for p in self.positions.values())
        return cash + position_value

    def get_total_exposure(self) -> float:
        """
        Get total capital at risk in active positions

        Returns:
            Total cost of active positions
        """
        return sum(p.total_cost for p in self.positions.values())

    def get_unrealized_pnl(self) -> float:
        """
        Get total unrealized P&L

        Returns:
            Sum of unrealized P&L across all positions
        """
        return sum(p.unrealized_pnl for p in self.positions.values())

    def get_realized_pnl(self) -> float:
        """
        Get total realized P&L

        Returns:
            Sum of realized P&L from settled positions
        """
        return sum(s.realized_pnl for s in self.settled_positions)

    def get_total_pnl(self) -> float:
        """
        Get total P&L (realized + unrealized)

        Returns:
            Total profit/loss
        """
        return self.get_realized_pnl() + self.get_unrealized_pnl()

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate performance report

        Returns:
            Dictionary with performance metrics
        """
        total_settled = len(self.settled_positions)
        wins = sum(1 for s in self.settled_positions if s.won)
        losses = total_settled - wins

        realized_pnl = self.get_realized_pnl()
        unrealized_pnl = self.get_unrealized_pnl()
        total_pnl = realized_pnl + unrealized_pnl

        portfolio_value = self.get_portfolio_value()
        total_return_pct = ((portfolio_value - self.starting_balance) / self.starting_balance * 100
                           if self.starting_balance > 0 else 0)

        return {
            # Balance
            'starting_balance': self.starting_balance,
            'current_balance': self.current_balance,
            'portfolio_value': portfolio_value,

            # Positions
            'active_positions': len(self.positions),
            'settled_positions': total_settled,
            'total_exposure': self.get_total_exposure(),

            # P&L
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,

            # Win rate
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / total_settled * 100) if total_settled > 0 else 0,

            # Average trade
            'avg_trade_pnl': (realized_pnl / total_settled) if total_settled > 0 else 0,
        }

    def print_summary(self) -> None:
        """Print portfolio summary to console"""
        report = self.get_performance_report()

        print("\n" + "=" * 80)
        print("PORTFOLIO SUMMARY")
        print("=" * 80)

        print(f"\n💰 Balance:")
        print(f"   Starting: ${report['starting_balance']:.2f}")
        print(f"   Current:  ${report['current_balance']:.2f}")
        print(f"   Portfolio Value: ${report['portfolio_value']:.2f}")

        print(f"\n📊 Positions:")
        print(f"   Active: {report['active_positions']}")
        print(f"   Settled: {report['settled_positions']}")
        print(f"   Total Exposure: ${report['total_exposure']:.2f}")

        print(f"\n💵 P&L:")
        print(f"   Realized:   ${report['realized_pnl']:+.2f}")
        print(f"   Unrealized: ${report['unrealized_pnl']:+.2f}")
        print(f"   Total:      ${report['total_pnl']:+.2f}")
        print(f"   Return:     {report['total_return_pct']:+.2f}%")

        print(f"\n🎯 Performance:")
        print(f"   Wins: {report['wins']}")
        print(f"   Losses: {report['losses']}")
        print(f"   Win Rate: {report['win_rate']:.1f}%")
        print(f"   Avg Trade P&L: ${report['avg_trade_pnl']:+.2f}")

        print()

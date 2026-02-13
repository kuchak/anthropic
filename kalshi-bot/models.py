"""
Data models for Kalshi trading bot
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class OrderSide(Enum):
    YES = "yes"
    NO = "no"


class TradeStatus(Enum):
    MOCK_FILLED = "mock_filled"
    SUBMITTED = "submitted"
    FILLED = "filled"
    REJECTED = "rejected"
    SETTLED_WIN = "settled_win"
    SETTLED_LOSS = "settled_loss"


@dataclass
class Market:
    """Represents a Kalshi market"""
    ticker: str
    title: str
    category: str
    settlement_time: datetime
    status: str
    best_yes_price: float
    best_no_price: float
    best_yes_size: int = 0
    best_no_size: int = 0

    @property
    def time_to_settlement_minutes(self) -> float:
        """Calculate minutes until settlement"""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if self.settlement_time <= now:
            return 0.0
        delta = self.settlement_time - now
        return delta.total_seconds() / 60.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['settlement_time'] = self.settlement_time.isoformat()
        return d


@dataclass
class Opportunity:
    """Represents a scored trading opportunity"""
    market: Market
    side: OrderSide
    price: float
    expected_profit: float
    time_to_settlement: float  # hours
    score: float
    model_accuracy: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'market_ticker': self.market.ticker,
            'market_title': self.market.title,
            'category': self.market.category,
            'side': self.side.value,
            'price': self.price,
            'expected_profit': self.expected_profit,
            'time_to_settlement': self.time_to_settlement,
            'score': self.score,
            'model_accuracy': self.model_accuracy
        }


@dataclass
class Allocation:
    """Position sizing decision"""
    opportunity: Opportunity
    num_contracts: int

    @property
    def total_cost(self) -> float:
        return self.num_contracts * self.opportunity.price


@dataclass
class Trade:
    """Represents an executed trade"""
    trade_id: str
    timestamp: datetime
    market_ticker: str
    market_title: str
    category: str
    settlement_time: datetime
    side: OrderSide
    price: float
    num_contracts: int
    total_cost: float
    score: float
    model_accuracy: float
    status: TradeStatus
    order_id: Optional[str] = None

    # Settlement fields
    resolved_at: Optional[datetime] = None
    outcome: Optional[str] = None  # "won" or "lost"
    payout: Optional[float] = None
    profit: Optional[float] = None

    def settle(self, won: bool, resolved_at: datetime):
        """Mark trade as settled"""
        self.resolved_at = resolved_at
        self.outcome = "won" if won else "lost"

        if won:
            self.payout = self.num_contracts * 1.0  # $1 per contract
            self.profit = self.payout - self.total_cost
            self.status = TradeStatus.SETTLED_WIN
        else:
            self.payout = 0.0
            self.profit = -self.total_cost
            self.status = TradeStatus.SETTLED_LOSS

    def to_dict(self) -> Dict[str, Any]:
        return {
            'trade_id': self.trade_id,
            'timestamp': self.timestamp.isoformat(),
            'market_ticker': self.market_ticker,
            'market_title': self.market_title,
            'category': self.category,
            'settlement_time': self.settlement_time.isoformat(),
            'side': self.side.value,
            'price': self.price,
            'num_contracts': self.num_contracts,
            'total_cost': self.total_cost,
            'score': self.score,
            'model_accuracy': self.model_accuracy,
            'status': self.status.value,
            'order_id': self.order_id,
            'settlement': {
                'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
                'outcome': self.outcome,
                'payout': self.payout,
                'profit': self.profit
            } if self.resolved_at else None
        }


@dataclass
class Portfolio:
    """Portfolio state tracker"""
    starting_bankroll: float
    current_bankroll: float
    open_trades: list = field(default_factory=list)
    settled_trades: list = field(default_factory=list)

    # Daily tracking
    daily_pnl: float = 0.0
    daily_trade_count: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0

    @property
    def open_exposure(self) -> float:
        """Total capital tied up in open positions"""
        return sum(trade.total_cost for trade in self.open_trades)

    @property
    def available_capital(self) -> float:
        """Capital available for new trades"""
        return self.current_bankroll - self.open_exposure

    @property
    def total_pnl(self) -> float:
        """Total P&L since inception"""
        return self.current_bankroll - self.starting_bankroll

    def add_trade(self, trade: Trade):
        """Add new trade to portfolio"""
        self.open_trades.append(trade)
        self.daily_trade_count += 1

    def settle_trade(self, trade: Trade, won: bool):
        """Move trade from open to settled"""
        if trade in self.open_trades:
            self.open_trades.remove(trade)

        self.settled_trades.append(trade)
        self.current_bankroll += trade.profit
        self.daily_pnl += trade.profit

        # Update streak counters
        if won:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

    def reset_daily_stats(self):
        """Reset daily counters (call at start of new day)"""
        self.daily_pnl = 0.0
        self.daily_trade_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'starting_bankroll': self.starting_bankroll,
            'current_bankroll': self.current_bankroll,
            'total_pnl': self.total_pnl,
            'open_exposure': self.open_exposure,
            'available_capital': self.available_capital,
            'daily_pnl': self.daily_pnl,
            'daily_trade_count': self.daily_trade_count,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'num_open_trades': len(self.open_trades),
            'num_settled_trades': len(self.settled_trades)
        }


@dataclass
class BankrollSnapshot:
    """Point-in-time bankroll snapshot for growth tracking"""
    timestamp: datetime
    bankroll: float
    open_exposure: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'bankroll': self.bankroll,
            'open_exposure': self.open_exposure
        }

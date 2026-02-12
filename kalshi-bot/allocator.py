"""
Position Sizing Allocator
Uses Kelly Criterion for optimal position sizing
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from logger_setup import get_logger
from scorer import ScoredOpportunity

logger = get_logger("allocator")


@dataclass
class PositionAllocation:
    """
    Position sizing recommendation

    Attributes:
        opportunity: The underlying opportunity
        kelly_fraction: Raw Kelly fraction (0.0 - 1.0)
        adjusted_fraction: Kelly fraction after applying safety factor
        position_size_dollars: Dollar amount to allocate
        num_contracts: Number of contracts to buy
        reasoning: Human-readable explanation
    """
    opportunity: ScoredOpportunity
    kelly_fraction: float
    adjusted_fraction: float
    position_size_dollars: float
    num_contracts: int
    reasoning: str

    def __repr__(self) -> str:
        return (
            f"PositionAllocation("
            f"ticker={self.opportunity.market.ticker}, "
            f"side={self.opportunity.side}, "
            f"contracts={self.num_contracts}, "
            f"size=${self.position_size_dollars:.2f})"
        )


class Allocator:
    """
    Allocates capital using Kelly Criterion

    Kelly Formula:
        f* = (p * b - q) / b

        Where:
        - f* = fraction of capital to bet
        - p = probability of winning
        - q = probability of losing (1 - p)
        - b = odds received (profit/loss ratio)

    For prediction markets:
        - b = (1 - entry_price) / entry_price
        - We apply a fractional Kelly (e.g., 25%) for safety
    """

    def __init__(self, config: Dict[str, Any], current_balance: float):
        self.config = config
        self.current_balance = current_balance

        self.kelly_fraction = config.get('kelly_fraction', 0.25)
        self.max_position_size_pct = config.get('max_position_size_pct', 0.20)
        self.max_total_exposure_pct = config.get('max_total_exposure_pct', 0.80)
        self.min_position_size_dollars = config.get('min_position_size_dollars', 10.0)

        logger.info("Allocator initialized")
        logger.info(f"  Current balance: ${current_balance:.2f}")
        logger.info(f"  Kelly fraction: {self.kelly_fraction * 100:.0f}%")
        logger.info(f"  Max position size: {self.max_position_size_pct * 100:.0f}% of balance")
        logger.info(f"  Max total exposure: {self.max_total_exposure_pct * 100:.0f}% of balance")

    def allocate_positions(
        self,
        opportunities: List[ScoredOpportunity],
        current_exposure: float = 0.0
    ) -> List[PositionAllocation]:
        """
        Allocate capital across opportunities

        Args:
            opportunities: Ranked list of opportunities
            current_exposure: Current dollar amount already allocated

        Returns:
            List of position allocations, ordered by priority
        """
        allocations = []
        remaining_capital = self.current_balance * self.max_total_exposure_pct - current_exposure

        logger.debug(f"Allocating across {len(opportunities)} opportunities")
        logger.debug(f"  Available capital: ${remaining_capital:.2f}")

        for opp in opportunities:
            # Check if we have capital left
            if remaining_capital < self.min_position_size_dollars:
                logger.debug(f"  Insufficient capital remaining (${remaining_capital:.2f})")
                break

            # Calculate Kelly fraction
            allocation = self._calculate_allocation(opp, remaining_capital)

            if allocation and allocation.position_size_dollars >= self.min_position_size_dollars:
                allocations.append(allocation)
                remaining_capital -= allocation.position_size_dollars
                logger.debug(f"  Allocated ${allocation.position_size_dollars:.2f} to {opp.market.ticker}")
            else:
                logger.debug(f"  Skipped {opp.market.ticker} - allocation too small")

        logger.info(f"✅ Allocated ${sum(a.position_size_dollars for a in allocations):.2f} across {len(allocations)} positions")

        return allocations

    def _calculate_allocation(
        self,
        opportunity: ScoredOpportunity,
        available_capital: float
    ) -> Optional[PositionAllocation]:
        """
        Calculate position size for one opportunity using Kelly Criterion

        Args:
            opportunity: Opportunity to size
            available_capital: Capital available for allocation

        Returns:
            PositionAllocation or None if allocation is invalid
        """
        # Extract values
        p = opportunity.win_probability  # Probability of winning
        q = 1 - p  # Probability of losing
        entry_price = opportunity.entry_price

        # Calculate odds
        # b = profit_if_win / loss_if_lose
        profit_if_win = 1.0 - entry_price
        loss_if_lose = entry_price
        b = profit_if_win / loss_if_lose if loss_if_lose > 0 else 0

        # Kelly formula: f* = (p * b - q) / b
        kelly_fraction = (p * b - q) / b if b > 0 else 0

        # Safety check - Kelly should be positive for profitable bets
        if kelly_fraction <= 0:
            logger.debug(f"  {opportunity.market.ticker}: Kelly fraction non-positive ({kelly_fraction:.4f})")
            return None

        # Apply fractional Kelly (e.g., 25% of full Kelly)
        adjusted_fraction = kelly_fraction * self.kelly_fraction

        # Calculate position size
        position_size_dollars = self.current_balance * adjusted_fraction

        # Apply maximum position size cap
        max_position = self.current_balance * self.max_position_size_pct
        if position_size_dollars > max_position:
            position_size_dollars = max_position
            reasoning = f"Capped at {self.max_position_size_pct * 100:.0f}% of balance"
        else:
            reasoning = f"{self.kelly_fraction * 100:.0f}% Kelly"

        # Check available capital
        if position_size_dollars > available_capital:
            position_size_dollars = available_capital
            reasoning = "Limited by available capital"

        # Calculate number of contracts
        # Each contract costs entry_price
        num_contracts = int(position_size_dollars / entry_price)

        # CRITICAL: Enforce minimum bet of 1 contract ($1.00)
        # If Kelly sizing produces less than 1 contract, round up to 1
        # This ensures we can participate in high-quality opportunities
        # even if Kelly suggests a tiny position
        if num_contracts < 1:
            # Check if we can afford 1 contract
            if entry_price <= available_capital and entry_price <= self.current_balance * self.max_position_size_pct:
                num_contracts = 1
                reasoning = "Rounded up to 1 contract minimum"
                logger.debug(f"  {opportunity.market.ticker}: Kelly suggested <1 contract, rounding up to 1")
            else:
                # Can't afford even 1 contract
                return None

        # Check minimum position size (should be at least $1 now)
        actual_position_size = num_contracts * entry_price
        if actual_position_size < 1.0:
            return None

        return PositionAllocation(
            opportunity=opportunity,
            kelly_fraction=kelly_fraction,
            adjusted_fraction=adjusted_fraction,
            position_size_dollars=actual_position_size,
            num_contracts=num_contracts,
            reasoning=reasoning
        )

    def get_max_allocatable_capital(self) -> float:
        """
        Get maximum capital available for allocation

        Returns:
            Dollar amount available
        """
        return self.current_balance * self.max_total_exposure_pct

    def update_balance(self, new_balance: float) -> None:
        """
        Update current balance

        Args:
            new_balance: New balance amount
        """
        old_balance = self.current_balance
        self.current_balance = new_balance
        logger.info(f"Balance updated: ${old_balance:.2f} → ${new_balance:.2f}")

    def get_stats(self, allocations: List[PositionAllocation]) -> Dict[str, Any]:
        """
        Get allocation statistics

        Args:
            allocations: List of allocations

        Returns:
            Dictionary of statistics
        """
        if not allocations:
            return {
                'total_positions': 0,
                'total_allocated': 0,
                'total_contracts': 0,
                'avg_position_size': 0,
                'largest_position': 0,
                'smallest_position': 0,
                'pct_of_balance_allocated': 0
            }

        total_allocated = sum(a.position_size_dollars for a in allocations)
        position_sizes = [a.position_size_dollars for a in allocations]

        return {
            'total_positions': len(allocations),
            'total_allocated': total_allocated,
            'total_contracts': sum(a.num_contracts for a in allocations),
            'avg_position_size': total_allocated / len(allocations),
            'largest_position': max(position_sizes),
            'smallest_position': min(position_sizes),
            'pct_of_balance_allocated': (total_allocated / self.current_balance * 100) if self.current_balance > 0 else 0
        }

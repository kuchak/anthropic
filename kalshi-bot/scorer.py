"""
Opportunity Scorer
Ranks trading opportunities by expected profit (after fees)
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import math
from logger_setup import get_logger
from models import Market

logger = get_logger("scorer")


@dataclass
class ScoredOpportunity:
    """
    A trading opportunity with calculated metrics

    Attributes:
        market: The underlying market
        side: "YES" or "NO" - which side to buy
        entry_price: Price we'd pay to enter
        win_probability: Our estimated probability of winning (from backtests)
        expected_profit: Expected profit per contract (AFTER FEES)
        expected_roi: Expected return on investment (%) (AFTER FEES)
        rank_score: Final ranking score (higher = better)
        time_to_settlement_hours: Hours until settlement
        estimated_fee_per_contract: Kalshi's estimated fee per contract
    """
    market: Market
    side: str
    entry_price: float
    win_probability: float
    expected_profit: float
    expected_roi: float
    rank_score: float
    time_to_settlement_hours: float
    estimated_fee_per_contract: float

    def __repr__(self) -> str:
        return (
            f"ScoredOpportunity("
            f"ticker={self.market.ticker}, "
            f"side={self.side}, "
            f"entry_price=${self.entry_price:.2f}, "
            f"expected_roi={self.expected_roi:.1f}%, "
            f"rank_score={self.rank_score:.2f})"
        )


class Scorer:
    """
    Scores and ranks trading opportunities

    Uses backtest accuracy data to calculate:
    - Win probability
    - Expected profit (AFTER FEES)
    - Expected ROI (AFTER FEES)
    - Rank score

    Key insight from backtests:
    - 85-89¢ contracts: 91.2% accuracy (11 wins, 1 loss, 91.7% avg profit)
    - 90-95¢ contracts: 89.4% accuracy (84/94 wins, 89.4% avg profit)
    - Overall 85-98¢: ~90% accuracy

    Kalshi Fees (Market taker):
    - Fee = ceil(7% × contracts × price × (1 - price))
    - Lower for market makers (limit orders)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Load accuracy data from config
        self.accuracy_by_price_range = config.get('accuracy_by_price_range', {})
        self.default_accuracy = config.get('default_accuracy', 0.90)

        # Load series ticker accuracy (highest priority - for whitelisted markets)
        self.series_ticker_accuracy = config.get('series_ticker_accuracy', {})

        # Load category accuracy overrides
        self.category_accuracy = config.get('category_accuracy', {})
        self.category_threshold = config.get('category_accuracy_threshold', 0.95)

        # Fee configuration
        self.fee_rate = config.get('kalshi_fee_rate', 0.07)  # 7% for takers

        logger.info("Scorer initialized")
        logger.info(f"  Default accuracy: {self.default_accuracy * 100:.1f}%")
        logger.info(f"  Series ticker accuracies: {len(self.series_ticker_accuracy)} series (whitelisted NBA markets)")
        logger.info(f"  Price range accuracies: {len(self.accuracy_by_price_range)} ranges configured")
        logger.info(f"  Category overrides: {len(self.category_accuracy)} categories (<{self.category_threshold*100:.0f}% threshold)")
        logger.info(f"  Kalshi fee rate: {self.fee_rate * 100:.1f}% (taker)")

    @staticmethod
    def calculate_fee_per_contract(price: float, fee_rate: float = 0.07) -> float:
        """
        Calculate Kalshi's fee per contract

        Formula: fee = ceil(fee_rate × price × (1 - price))

        This is for TAKER orders (market orders).
        MAKER orders (limit orders) have lower fees.

        Args:
            price: Contract price (0.0 - 1.0)
            fee_rate: Fee rate (default 7% for takers)

        Returns:
            Fee per contract in dollars
        """
        fee = fee_rate * price * (1.0 - price)
        # Round up to nearest cent
        return math.ceil(fee * 100) / 100

    def score_markets(self, markets: List[Market]) -> List[ScoredOpportunity]:
        """
        Score all markets and return ranked opportunities

        Args:
            markets: List of markets to score

        Returns:
            List of scored opportunities, sorted by rank (best first)
        """
        opportunities = []

        for market in markets:
            # Score both YES and NO sides
            yes_opp = self._score_market_side(market, "YES")
            no_opp = self._score_market_side(market, "NO")

            # Add valid opportunities (must have positive ROI AFTER fees)
            if yes_opp and yes_opp.expected_roi > 0:
                opportunities.append(yes_opp)

            if no_opp and no_opp.expected_roi > 0:
                opportunities.append(no_opp)

        # Sort by rank score (descending)
        opportunities.sort(key=lambda x: x.rank_score, reverse=True)

        logger.debug(f"Scored {len(markets)} markets → {len(opportunities)} valid opportunities")

        return opportunities

    def _score_market_side(self, market: Market, side: str) -> Optional[ScoredOpportunity]:
        """
        Score one side of a market (YES or NO)

        Args:
            market: Market to score
            side: "YES" or "NO"

        Returns:
            ScoredOpportunity or None if invalid
        """
        # Get entry price
        entry_price = market.best_yes_price if side == "YES" else market.best_no_price

        # Validate price is in target range
        if not (self.config['min_contract_price'] <= entry_price <= self.config['max_contract_price']):
            return None

        # Calculate win probability based on price range AND category
        # Uses conservative override: if category accuracy < 95%, uses min(price_acc, category_acc)
        win_probability = self._get_win_probability(entry_price, market.category)

        # Calculate Kalshi fees (per contract)
        fee_per_contract = self.calculate_fee_per_contract(entry_price, self.fee_rate)

        # Calculate expected profit AFTER FEES
        # Win: Profit = $1.00 - entry_price - fee
        # Loss: Loss = entry_price + fee
        # Expected profit = P(win) * profit - P(loss) * loss
        profit_if_win = 1.0 - entry_price - fee_per_contract
        loss_if_loss = entry_price + fee_per_contract

        expected_profit = (win_probability * profit_if_win) - ((1 - win_probability) * loss_if_loss)
        expected_roi = (expected_profit / entry_price) * 100 if entry_price > 0 else 0

        # Calculate rank score
        # Higher score = better opportunity
        # Factors:
        # 1. Expected ROI (primary)
        # 2. Time to settlement (prefer shorter)
        # 3. Win probability (prefer higher confidence)

        time_to_settlement_hours = market.time_to_settlement_minutes / 60

        # Normalize time factor (prefer 1-3 hours, penalize very short or very long)
        if time_to_settlement_hours < 1:
            time_factor = 0.7  # Too risky - not much time to analyze
        elif time_to_settlement_hours < 3:
            time_factor = 1.0  # Sweet spot
        elif time_to_settlement_hours < 6:
            time_factor = 0.9  # Still good
        else:
            time_factor = 0.8  # Capital tied up longer

        # Confidence boost for high-accuracy ranges
        confidence_factor = 1.0 + (win_probability - self.default_accuracy) * 2

        # Final rank score
        rank_score = expected_roi * time_factor * confidence_factor

        return ScoredOpportunity(
            market=market,
            side=side,
            entry_price=entry_price,
            win_probability=win_probability,
            expected_profit=expected_profit,
            expected_roi=expected_roi,
            rank_score=rank_score,
            time_to_settlement_hours=time_to_settlement_hours,
            estimated_fee_per_contract=fee_per_contract
        )

    def _get_win_probability(self, price: float, category: str = None) -> float:
        """
        Get win probability based on series ticker, price range, and category

        Priority order (highest to lowest):
        1. Series ticker accuracy (for whitelisted NBA markets with 100%/93% accuracy)
        2. Category accuracy (if below 95% threshold, uses conservative estimate)
        3. Price-based accuracy (default fallback)

        Args:
            price: Contract price (0.0 - 1.0)
            category: Market category / series ticker (optional)

        Returns:
            Win probability (0.0 - 1.0) - conservative estimate
        """
        # PRIORITY 1: Check series ticker accuracy (for whitelisted markets)
        # category field stores series_ticker from the API
        if category and category in self.series_ticker_accuracy:
            series_acc = self.series_ticker_accuracy[category]
            logger.debug(f"Using series ticker accuracy for {category}: {series_acc:.3f}")
            return series_acc

        # PRIORITY 2: Get price-based accuracy
        price_accuracy = self.default_accuracy
        for price_range, accuracy in self.accuracy_by_price_range.items():
            # Parse range like "0.85-0.89" or "0.90-0.95"
            if '-' in price_range:
                min_price, max_price = map(float, price_range.split('-'))
                if min_price <= price <= max_price:
                    price_accuracy = accuracy
                    break

        # PRIORITY 3: Check category override (conservative approach)
        if category and category in self.category_accuracy:
            category_acc = self.category_accuracy[category]

            # If category accuracy is below threshold, use the MORE CONSERVATIVE estimate
            if category_acc < self.category_threshold:
                # Use the lower of the two
                conservative_accuracy = min(price_accuracy, category_acc)
                logger.debug(f"Category override for {category}: "
                           f"price={price_accuracy:.3f}, category={category_acc:.3f}, "
                           f"using={conservative_accuracy:.3f}")
                return conservative_accuracy

        # Use price-based accuracy (category is good or not found)
        return price_accuracy

    def get_top_opportunities(self, markets: List[Market], limit: int = 10) -> List[ScoredOpportunity]:
        """
        Get top N trading opportunities

        Args:
            markets: List of markets to score
            limit: Maximum number of opportunities to return

        Returns:
            Top opportunities by rank score
        """
        all_opportunities = self.score_markets(markets)
        return all_opportunities[:limit]

    def get_stats(self, opportunities: List[ScoredOpportunity]) -> Dict[str, Any]:
        """
        Get statistics about scored opportunities

        Args:
            opportunities: List of scored opportunities

        Returns:
            Dictionary of statistics
        """
        if not opportunities:
            return {
                'total_opportunities': 0,
                'avg_expected_roi': 0,
                'avg_win_probability': 0,
                'avg_time_to_settlement_hours': 0
            }

        return {
            'total_opportunities': len(opportunities),
            'avg_expected_roi': sum(o.expected_roi for o in opportunities) / len(opportunities),
            'avg_win_probability': sum(o.win_probability for o in opportunities) / len(opportunities),
            'avg_time_to_settlement_hours': sum(o.time_to_settlement_hours for o in opportunities) / len(opportunities),
            'best_roi': max(o.expected_roi for o in opportunities),
            'worst_roi': min(o.expected_roi for o in opportunities),
        }

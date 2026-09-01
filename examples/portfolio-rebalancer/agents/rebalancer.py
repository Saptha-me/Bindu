from shared.types import DriftResult, TradeAction, TradePlan, PortfolioRisk
from shared.config import REBALANCE_FRACTION

DRIFT_THRESHOLD  = 5.0
RISK_HIGH        = 7.0
RISK_LOW         = 4.0
RISK_HIGH_MULT   = 1.2
RISK_LOW_MULT    = 0.8
LOW_TRADE_MULT   = 0.7


def run(
    portfolio_id: str,
    drift: list[DriftResult],
    portfolio_risk: PortfolioRisk,
    memory: dict,
    portfolio_value: float
) -> TradePlan:
    print(f"[rebalancer] portfolio_value received: {portfolio_value}")
    actions: list[TradeAction] = []

    low_trade = memory.get("preferences", {}).get("low_trade_frequency", False)

    # --- global risk multiplier ---
    if portfolio_risk.total_score > RISK_HIGH:
        risk_multiplier = RISK_HIGH_MULT
    elif portfolio_risk.total_score < RISK_LOW:
        risk_multiplier = RISK_LOW_MULT
    else:
        risk_multiplier = 1.0

    if low_trade:
        risk_multiplier *= LOW_TRADE_MULT

    # --- actions ---
    for d in drift:
        symbol = d.symbol
        drift_pct = d.drift_pct

        action = "hold"
        amount = 0.0
        reason = "within acceptable range"

        if drift_pct > DRIFT_THRESHOLD:
            action = "sell"
        elif drift_pct < -DRIFT_THRESHOLD:
            action = "buy"

        if action != "hold":
            base_amount = abs(drift_pct) / 100 * portfolio_value
            amount = base_amount * REBALANCE_FRACTION * risk_multiplier

            reason = f"{symbol} drift {drift_pct:+.1f}%"

            if portfolio_risk.total_score > RISK_HIGH:
                reason += " + high risk"

            if low_trade:
                reason += " + low frequency mode"

        actions.append(
            TradeAction(
                symbol=symbol,
                action=action,
                amount_usd=round(amount, 2),
                reason=reason
            )
        )

    # --- summary ---
    total_sell = sum(a.amount_usd for a in actions if a.action == "sell")
    total_buy  = sum(a.amount_usd for a in actions if a.action == "buy")

    summary = (
        f"Rebalance by selling ${total_sell:,.0f} and buying ${total_buy:,.0f}. "
        f"{portfolio_risk.summary}"
    )

    # --- memory update ---
    memory_update = {
        "last_rebalance": "executed",
        "last_risk_score": portfolio_risk.total_score,
    }

    return TradePlan(
        portfolio_id=portfolio_id,
        actions=actions,
        risk_summary=summary,
        memory_update=memory_update
    )
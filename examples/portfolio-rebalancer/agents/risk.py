from shared.types import DriftResult, RiskScore, PortfolioRisk

# lightweight asset risk tiers
RISK_TIERS = {
    "BTC": 7.0,
    "ETH": 5.5,
    "SOL": 6.5,
    "BNB": 5.0,
    "USDC": 1.0,
    "USDT": 1.0,
    "DOGE": 9.0,
}

HIGH_CONCENTRATION = 50
MOD_CONCENTRATION  = 30


def run(drift: list[DriftResult]) -> tuple[list[RiskScore], PortfolioRisk]:
    risk_scores: list[RiskScore] = []
    total_score = 0.0
    flags: list[str] = []

    for d in drift:
        symbol = d.symbol
        pct = d.current_pct

        # --- base score from tier ---
        score = RISK_TIERS.get(symbol, 5.0)
        reason = "baseline risk"

        # --- stable assets ---
        if symbol in ["USDC", "USDT"]:
            reason = "stable asset"

        # --- concentration adjustment ---
        elif pct > HIGH_CONCENTRATION:
            score += 2.0
            reason = "high concentration"
            flags.append(f"{symbol}_overweight")

        elif pct > MOD_CONCENTRATION:
            score += 1.0
            reason = "moderate concentration"

        # cap score to 10
        score = min(score, 10.0)

        risk_scores.append(
            RiskScore(
                symbol=symbol,
                score=round(score, 1),
                reason=reason
            )
        )

        total_score += score

    # --- portfolio risk ---
    avg_score = total_score / len(risk_scores) if risk_scores else 0.0
    avg_score = round(avg_score, 2)

    # --- smarter summary ---
    high_risk_assets = [r.symbol for r in risk_scores if r.score >= 7]

    if avg_score >= 7:
        summary = f"High portfolio risk driven by {', '.join(high_risk_assets)}"
    elif avg_score >= 4:
        summary = "Moderate portfolio risk"
    else:
        summary = "Low portfolio risk"

    portfolio_risk = PortfolioRisk(
        total_score=avg_score,
        summary=summary
    )

    return risk_scores, portfolio_risk
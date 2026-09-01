from shared.types import Portfolio, TargetAllocation, DriftResult


def run(portfolio: Portfolio, target: TargetAllocation) -> list[DriftResult]:
    results: list[DriftResult] = []

    total_value = portfolio.total_value

    if total_value == 0:
        return []

    for asset in portfolio.assets:
        symbol = asset.symbol

        current_pct = (asset.current_value / total_value) * 100
        target_pct = target.get(symbol, 0.0)

        drift_pct = current_pct - target_pct

        results.append(
            DriftResult(
                symbol=symbol,
                current_pct=round(current_pct, 2),
                target_pct=round(target_pct, 2),
                drift_pct=round(drift_pct, 2),
            )
        )

    return results
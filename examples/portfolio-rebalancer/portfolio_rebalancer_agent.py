from bindu.penguin.bindufy import bindufy

from agents import analyst, pricer, risk, rebalancer
from shared.memory import SemanticMemory
from shared.types import Portfolio, Asset




config = {
    "author": "akash",
    "name": "portfolio-rebalancer-agent",
    "version": "1.0.0",
    "description": "Multi-agent system for portfolio drift analysis, risk scoring, and adaptive rebalancing using semantic memory",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "capabilities": {"payments": []},
    "skills": ["skills/portfolio-rebalancer-agent-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
}


def handler(messages):
    memory = SemanticMemory()

    if not isinstance(messages, list) or len(messages) == 0:
        return {"error": "Invalid messages format"}

    # --- GET LAST USER MESSAGE ---
    last_msg = messages[-1]
    if not isinstance(last_msg, dict):
        return {"error": "Invalid last message format"}
    content = last_msg.get("content", {})

    if not isinstance(content, dict):
        return {"error": "Expected JSON content in last message"}

    raw_portfolio = content.get("portfolio", {})
    target = content.get("target", {})

    if not raw_portfolio or "assets" not in raw_portfolio:
        return {"error": "Missing portfolio data"}

    # --- PARSE ASSETS ---
    assets = []
    for a in raw_portfolio.get("assets", []):
        if "symbol" in a and "current_value" in a:
            try:
                current_value = float(a["current_value"])
            except (TypeError, ValueError):
                continue
            assets.append(Asset(
                symbol=a["symbol"],
                current_value=current_value,
                target_pct=target.get(a["symbol"], 0)
            ))

    if not assets:
        return {"error": "No valid assets found in portfolio"}

    portfolio = Portfolio(
        id=raw_portfolio.get("id", "unknown"),
        assets=assets
    )

    # --- PIPELINE ---
    drift = analyst.run(portfolio, target)

    symbols = [a.symbol for a in portfolio.assets]
    prices = pricer.run(symbols)

    _, portfolio_risk = risk.run(drift)
    portfolio_value = portfolio.total_value
    
    result = rebalancer.run(
        portfolio_id=portfolio.id,
        drift=drift,
        portfolio_risk=portfolio_risk,
        memory=memory.get(),
        portfolio_value=portfolio_value
    )

    memory.update(result.memory_update)

    # --- RESPONSE ---
    return {
        "role": "assistant",
        "content": {
            "portfolio_id": portfolio.id,
            "prices": prices,
            "actions": [
                {
                    "symbol": a.symbol,
                    "action": a.action,
                    "amount_usd": a.amount_usd,
                    "reason": a.reason,
                }
                for a in result.actions
            ],
            "summary": result.risk_summary,
            "timestamp": result.created_at,
            "memory": memory.get()
        }
    }


if __name__ == "__main__":
    print("Portfolio Rebalancer Agent running on Bindu...")
    bindufy(config, handler)
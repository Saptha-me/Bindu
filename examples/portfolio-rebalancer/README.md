# Portfolio Rebalancer — Bindu Multi-Agent Example

A multi-agent system that analyzes portfolio allocation, evaluates risk,
and generates rebalancing recommendations using semantic memory.

## Architecture

Four specialized agents, orchestrated by a central handler:


Analyst - Computes current allocation and drift from target 
Pricer - Fetches live prices via CoinGecko (with fallback)
Risk - Scores asset-level and portfolio-level risk 
Rebalancer - Generates trade actions based on drift + risk

All agents share a semantic memory layer that persists preferences
and past rebalance history across runs.

## Setup
```bash
cd examples/portfolio-rebalancer
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
```bash
COINGECKO_API_KEY=optional
USE_FAKE_DATA=false
REQUEST_TIMEOUT=5
REBALANCE_FRACTION=0.25
```

## Run
```bash
python portfolio_rebalancer_agent.py
```

## Example

Input:
```python
Portfolio(
    id="demo-portfolio-001",
    assets=[
        Asset(symbol="BTC",  current_value=35000, target_pct=25),
        Asset(symbol="ETH",  current_value=8000,  target_pct=20),
        Asset(symbol="SOL",  current_value=2000,  target_pct=15),
        Asset(symbol="BNB",  current_value=9000,  target_pct=15),
        Asset(symbol="USDC", current_value=12500, target_pct=20),
        Asset(symbol="DOGE", current_value=13500, target_pct=5),
    ]
)
```

Output:
```bash
=== PRICES ===
{'BTC': 69675, 'ETH': 2152.05, 'SOL': 82.49, 'BNB': 605.69, 'USDC': 1.0, 'DOGE': 0.092936}

=== DRIFT ANALYSIS ===
BTC    current 43.8%  target 25.0%  drift +18.8%
ETH    current 10.0%  target 20.0%  drift -10.0%
SOL    current  2.5%  target 15.0%  drift -12.5%
BNB    current 11.2%  target 15.0%  drift  -3.8%  → hold
USDC   current 15.6%  target 20.0%  drift  -4.4%  → hold
DOGE   current 16.9%  target  5.0%  drift +11.9%

=== RISK SCORES ===
BTC    ████████░░  8.0/10  moderate concentration
ETH    █████░░░░░  5.5/10  baseline risk
SOL    ██████░░░░  6.5/10  baseline risk
BNB    █████░░░░░  5.0/10  baseline risk
USDC   █░░░░░░░░░  1.0/10  stable asset
DOGE   █████████░  9.0/10  baseline risk

=== TRADE PLAN ===
▼ BTC    SELL  $  3,750.00   BTC drift +18.8% (25% rebalance)
▲ ETH    BUY   $  2,000.00   ETH drift -10.0% (25% rebalance)
▲ SOL    BUY   $  2,500.00   SOL drift -12.5% (25% rebalance)
— BNB    HOLD  $      0.00   within acceptable range
— USDC   HOLD  $      0.00   within acceptable range
▼ DOGE   SELL  $  2,376.00   DOGE drift +11.9% (25% rebalance)

=== SUMMARY ===
Partial rebalance (25% of drift): Sell $6,126 / Buy $4,500.
Full rebalance would be: Sell $24,504 / Buy $18,000.
High risk assets: BTC, DOGE.
```

## Structure
```bash
examples/portfolio-rebalancer/
├── portfolio_rebalancer_agent.py   # bindufy() entry + orchestration
├── analyst.py                      # drift detection
├── pricer.py                       # CoinGecko price fetch
├── risk.py                         # volatility scoring
├── rebalancer.py                   # trade plan generation
├── types.py                        # shared dataclasses
├── memory.py                       # semantic memory layer
├── config.py                       # env config
├── demo.py                         # end-to-end demo runner
├── skill.yaml                      # Bindu skill descriptor
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- `REBALANCE_FRACTION=0.25` means each run rebalances 25% of drift —
  set to `1.0` for a full rebalance in one pass
- Risk scores influence trade sizing via a configurable multiplier
- Prices fall back to static values if CoinGecko is unavailable
- Memory persists last risk score and rebalance totals across runs
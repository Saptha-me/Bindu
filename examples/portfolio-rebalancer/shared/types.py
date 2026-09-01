from dataclasses import dataclass, field
from typing import Literal, Dict
from datetime import datetime


@dataclass
class Asset:
    symbol: str
    current_value: float
    target_pct: float = 0.0


@dataclass
class Portfolio:
    id: str
    assets: list[Asset]
    currency: str = "USD"

    @property
    def total_value(self) -> float:
        return sum(a.current_value for a in self.assets)


TargetAllocation = Dict[str, float]


@dataclass
class DriftResult:
    symbol: str
    current_pct: float
    target_pct: float
    drift_pct: float


@dataclass
class RiskScore:
    symbol: str
    score: float
    reason: str


@dataclass
class PortfolioRisk:
    total_score: float
    summary: str


@dataclass
class TradeAction:
    symbol: str
    action: Literal["buy", "sell", "hold"]
    amount_usd: float
    reason: str


@dataclass
class TradePlan:
    portfolio_id: str
    actions: list[TradeAction]
    risk_summary: str
    memory_update: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
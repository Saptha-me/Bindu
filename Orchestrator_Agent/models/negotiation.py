import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class NegotiationStatus(Enum):
    """Negotiation workflow status"""
    INITIATED = "initiated"
    QUOTED = "quoted"
    COUNTER_OFFERED = "counter_offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class NegotiationRole(Enum):
    """Role in negotiation"""
    REQUESTER = "requester"  # Orchestrator
    PROVIDER = "provider"    # Agent


@dataclass
class PriceQuote:
    """Represents a price quote from an agent"""
    agent_did: str
    task_id: str
    subtask_id: str
    base_cost: float
    currency: str = "USD"
    execution_time_estimate: int = 60  # seconds
    quality_guarantee: float = 0.95  # quality score guarantee
    payment_address: str = ""  # X402 payment address
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if quote has expired"""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires

    def total_cost(self) -> float:
        """Calculate total cost including any fees"""
        return self.base_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "agent_did": self.agent_did,
            "task_id": self.task_id,
            "subtask_id": self.subtask_id,
            "base_cost": self.base_cost,
            "currency": self.currency,
            "execution_time_estimate": self.execution_time_estimate,
            "quality_guarantee": self.quality_guarantee,
            "total_cost": self.total_cost(),
            "is_expired": self.is_expired(),
            "payment_address": self.payment_address,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class NegotiationOffer:
    """Represents a negotiation offer"""
    offer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    subtask_id: str = ""
    requester_did: str = ""  # Orchestrator DID
    provider_did: str = ""   # Agent DID
    requested_price: float = 0.0
    offered_price: float = 0.0
    currency: str = "USD"
    payment_method: str = "x402"
    status: NegotiationStatus = NegotiationStatus.INITIATED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def accept(self) -> None:
        """Accept the offer"""
        self.status = NegotiationStatus.ACCEPTED
        self.updated_at = datetime.utcnow().isoformat()

    def reject(self) -> None:
        """Reject the offer"""
        self.status = NegotiationStatus.REJECTED
        self.updated_at = datetime.utcnow().isoformat()

    def counter_offer(self, new_price: float) -> None:
        """Send a counter offer"""
        self.offered_price = new_price
        self.status = NegotiationStatus.COUNTER_OFFERED
        self.updated_at = datetime.utcnow().isoformat()

    def is_expired(self) -> bool:
        """Check if offer has expired"""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "offer_id": self.offer_id,
            "task_id": self.task_id,
            "subtask_id": self.subtask_id,
            "requester_did": self.requester_did,
            "provider_did": self.provider_did,
            "requested_price": self.requested_price,
            "offered_price": self.offered_price,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired(),
        }


@dataclass
class Negotiation:
    """Represents a negotiation session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    subtask_id: str = ""
    agent_did: str = ""
    orchestrator_did: str = ""
    status: NegotiationStatus = NegotiationStatus.INITIATED
    
    # Pricing
    max_price: float = 0.0
    quoted_price: float = 0.0
    final_price: float = 0.0
    currency: str = "USD"
    
    # Offers
    offers: List[NegotiationOffer] = field(default_factory=list)
    quotes: List[PriceQuote] = field(default_factory=list)
    
    # Timeline
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Quality & SLA
    quality_guarantee: float = 0.95
    execution_time_estimate: int = 60  # seconds
    payment_address: str = ""  # X402 payment address
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_offer(self, offer: NegotiationOffer) -> None:
        """Add an offer to negotiation"""
        self.offers.append(offer)
        self.status = NegotiationStatus.COUNTER_OFFERED
        self.updated_at = datetime.utcnow().isoformat()

    def add_quote(self, quote: PriceQuote) -> None:
        """Add a quote to negotiation"""
        self.quotes.append(quote)
        self.quoted_price = quote.base_cost
        self.status = NegotiationStatus.QUOTED
        self.updated_at = datetime.utcnow().isoformat()

    def accept(self) -> None:
        """Accept the negotiation"""
        self.status = NegotiationStatus.ACCEPTED
        self.final_price = self.quoted_price
        self.updated_at = datetime.utcnow().isoformat()

    def reject(self) -> None:
        """Reject the negotiation"""
        self.status = NegotiationStatus.REJECTED
        self.updated_at = datetime.utcnow().isoformat()

    def is_expired(self) -> bool:
        """Check if negotiation has expired"""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires

    def is_acceptable(self) -> bool:
        """Check if current price is acceptable"""
        return self.quoted_price <= self.max_price

    def within_budget(self) -> bool:
        """Check if final price is within budget"""
        return self.final_price <= self.max_price

    def get_latest_offer(self) -> Optional[NegotiationOffer]:
        """Get the most recent offer"""
        if self.offers:
            return self.offers[-1]
        return None

    def get_latest_quote(self) -> Optional[PriceQuote]:
        """Get the most recent quote"""
        if self.quotes:
            return self.quotes[-1]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "subtask_id": self.subtask_id,
            "agent_did": self.agent_did,
            "orchestrator_did": self.orchestrator_did,
            "status": self.status.value,
            "max_price": self.max_price,
            "quoted_price": self.quoted_price,
            "final_price": self.final_price,
            "currency": self.currency,
            "quality_guarantee": self.quality_guarantee,
            "execution_time_estimate": self.execution_time_estimate,
            "offers_count": len(self.offers),
            "quotes_count": len(self.quotes),
            "is_acceptable": self.is_acceptable(),
            "within_budget": self.within_budget(),
            "is_expired": self.is_expired(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
import logging
import uuid
from typing import Optional, Dict, Any, List
from models.negotiation import Negotiation, PriceQuote, NegotiationOffer, NegotiationStatus
from models.agent_profile import AgentProfile
from models.task import SubTask
from utils.logger import get_logger


class AgentNegotiator:
    """Handles negotiation with agents for task execution"""
    
    def __init__(self, orchestrator_did: str):
        self.logger = get_logger(__name__)
        self.orchestrator_did = orchestrator_did
        self.negotiations: Dict[str, Negotiation] = {}
    
    def initiate_negotiation(self, agent: AgentProfile, subtask: SubTask, 
                            max_price: float) -> Negotiation:
        
        self.logger.info(f"Initiating negotiation with {agent.did} for subtask {subtask.id}")
        
        negotiation = Negotiation(
            task_id=subtask.parent_task_id,
            subtask_id=subtask.id,
            agent_did=agent.did,
            orchestrator_did=self.orchestrator_did,
            max_price=max_price,
            quality_guarantee=0.95,
            execution_time_estimate=subtask.estimated_duration,
        )
        
        self.negotiations[negotiation.id] = negotiation
        return negotiation
    
    def request_quote(self, negotiation: Negotiation, agent: AgentProfile, 
                     capability_name: str) -> Optional[PriceQuote]:
        """
        Request a price quote from an agent
        
        Args:
            negotiation: Negotiation context
            agent: Agent to request from
            capability_name: Capability to quote
            
        Returns:
            PriceQuote or None
        """
        self.logger.info(f"Requesting quote from {agent.did} for {capability_name}")
        
        # Get capability cost
        cost = agent.get_capability_cost(capability_name)
        if not cost:
            self.logger.warning(f"Agent {agent.did} doesn't have capability {capability_name}")
            return None
        
        # Create quote
        quote = PriceQuote(
            agent_did=agent.did,
            task_id=negotiation.task_id,
            subtask_id=negotiation.subtask_id,
            base_cost=cost,
            currency="USD",
            execution_time_estimate=negotiation.execution_time_estimate,
            quality_guarantee=agent.average_quality_score,
            payment_address=f"x402:{agent.did}"
        )
        
        self.logger.info(f"Received quote: ${quote.base_cost} from {agent.did}")
        return quote
    
    def process_quote(self, negotiation_id: str, quote: PriceQuote) -> bool:
        """
        Process a received quote
        
        Args:
            negotiation_id: Negotiation ID
            quote: Quote to process
            
        Returns:
            Success status
        """
        negotiation = self.negotiations.get(negotiation_id)
        if not negotiation:
            self.logger.error(f"Negotiation {negotiation_id} not found")
            return False
        
        negotiation.add_quote(quote)
        
        if negotiation.is_acceptable():
            self.logger.info(f"Quote is acceptable: ${quote.base_cost}")
            return True
        else:
            self.logger.warning(f"Quote exceeds budget: ${quote.base_cost} > ${negotiation.max_price}")
            return False
    
    def accept_quote(self, negotiation_id: str) -> bool:
        """
        Accept a quote
        
        Args:
            negotiation_id: Negotiation ID
            
        Returns:
            Success status
        """
        negotiation = self.negotiations.get(negotiation_id)
        if not negotiation:
            return False
        
        if not negotiation.is_acceptable():
            self.logger.warning(f"Cannot accept quote - exceeds budget")
            return False
        
        negotiation.accept()
        self.logger.info(f"Negotiation {negotiation_id} accepted")
        return True
    
    def reject_quote(self, negotiation_id: str) -> bool:
        """
        Reject a quote
        
        Args:
            negotiation_id: Negotiation ID
            
        Returns:
            Success status
        """
        negotiation = self.negotiations.get(negotiation_id)
        if not negotiation:
            return False
        
        negotiation.reject()
        self.logger.info(f"Negotiation {negotiation_id} rejected")
        return True
    
    def counter_offer(self, negotiation_id: str, new_price: float) -> bool:
        """
        Send a counter offer
        
        Args:
            negotiation_id: Negotiation ID
            new_price: Counter price
            
        Returns:
            Success status
        """
        negotiation = self.negotiations.get(negotiation_id)
        if not negotiation:
            return False
        
        offer = NegotiationOffer(
            task_id=negotiation.task_id,
            subtask_id=negotiation.subtask_id,
            requester_did=self.orchestrator_did,
            provider_did=negotiation.agent_did,
            requested_price=negotiation.quoted_price,
            offered_price=new_price,
        )
        
        negotiation.add_offer(offer)
        self.logger.info(f"Sent counter offer: ${new_price}")
        return True
    
    def get_negotiation(self, negotiation_id: str) -> Optional[Negotiation]:
        """Get negotiation by ID"""
        return self.negotiations.get(negotiation_id)
    
    def get_negotiations_by_status(self, status: NegotiationStatus) -> List[Negotiation]:
        """Get all negotiations with a specific status"""
        return [n for n in self.negotiations.values() if n.status == status]


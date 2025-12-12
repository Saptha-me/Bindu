import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime
from utils.logger import get_logger


class PaymentTransaction:
    """Represents a payment transaction"""
    
    def __init__(self, agent_did: str, amount: float, currency: str = "USD"):
        self.id = str(uuid.uuid4())
        self.agent_did = agent_did
        self.amount = amount
        self.currency = currency
        self.status = "pending"
        self.timestamp = datetime.utcnow().isoformat()
        self.tx_hash = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_did": self.agent_did,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "timestamp": self.timestamp,
            "tx_hash": self.tx_hash,
        }


class PaymentHandler:
    """Handles X402 payment settlement"""
    
    def __init__(self, orchestrator_did: str):
        self.logger = get_logger(__name__)
        self.orchestrator_did = orchestrator_did
        self.transactions: Dict[str, PaymentTransaction] = {}
        self.total_settled = 0.0
    
    def create_payment(self, agent_did: str, amount: float, 
                      currency: str = "USD") -> PaymentTransaction:

        transaction = PaymentTransaction(agent_did, amount, currency)
        self.transactions[transaction.id] = transaction
        
        self.logger.info(f"Created payment {transaction.id} to {agent_did} for ${amount}")
        return transaction
    
    def settle_payment(self, transaction_id: str) -> bool:

        transaction = self.transactions.get(transaction_id)
        if not transaction:
            self.logger.error(f"Payment {transaction_id} not found")
            return False
        
        try:
            # Simulate X402 payment settlement
            transaction.status = "completed"
            transaction.tx_hash = f"0x{uuid.uuid4().hex[:16]}"
            
            self.total_settled += transaction.amount
            self.logger.info(
                f"Payment settled: {transaction.id} to {transaction.agent_did} "
                f"for ${transaction.amount} (tx: {transaction.tx_hash})"
            )
            return True
            
        except Exception as e:
            transaction.status = "failed"
            self.logger.error(f"Payment settlement failed: {str(e)}")
            return False
    
    def batch_settle_payments(self, transaction_ids: List[str]) -> Dict[str, bool]:

        results = {}
        for tx_id in transaction_ids:
            results[tx_id] = self.settle_payment(tx_id)
        
        settled_count = sum(1 for v in results.values() if v)
        self.logger.info(f"Batch settlement: {settled_count}/{len(transaction_ids)} settled")
        
        return results
    
    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction details"""
        transaction = self.transactions.get(transaction_id)
        if transaction:
            return transaction.to_dict()
        return {}
    
    def get_settlement_summary(self) -> Dict[str, Any]:
        """Get settlement summary"""
        completed = [t for t in self.transactions.values() if t.status == "completed"]
        pending = [t for t in self.transactions.values() if t.status == "pending"]
        failed = [t for t in self.transactions.values() if t.status == "failed"]
        
        return {
            "total_transactions": len(self.transactions),
            "completed": len(completed),
            "pending": len(pending),
            "failed": len(failed),
            "total_settled": self.total_settled,
            "total_pending": sum(t.amount for t in pending),
        }
"""
Certificate renewal for mTLS.

This module handles automatic certificate renewal operations
to ensure certificates are always valid.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable

from pebbling.security.mtls.cert_lifecycle import CertLifecycleManager
from pebbling.security.mtls.cert_verification import CertVerificationManager

logger = logging.getLogger(__name__)


class CertRenewalManager:
    """Manages automatic certificate renewal.
    
    This class handles:
    1. Periodic checking of certificate validity
    2. Automatic renewal of certificates when needed
    """
    
    def __init__(
        self,
        lifecycle_manager: CertLifecycleManager,
        verification_manager: CertVerificationManager,
        auto_renewal: bool = True
    ):
        """Initialize the certificate renewal manager.
        
        Args:
            lifecycle_manager: Manager for certificate lifecycle operations
            verification_manager: Manager for certificate verification
            auto_renewal: Whether to automatically renew certificates
        """
        self.lifecycle_manager = lifecycle_manager
        self.verification_manager = verification_manager
        self.auto_renewal = auto_renewal
        self._renewal_task = None
            
    async def start_renewal_task(self, interval_days: int = 7) -> None:
        """Start a background task for certificate renewal.
        
        Args:
            interval_days: How often to check for renewal (in days)
            
        Returns:
            None
        """
        if not self.auto_renewal:
            logger.info("Automatic certificate renewal is disabled")
            return
            
        async def renewal_task():
            while True:
                try:
                    # Sleep first to avoid immediate renewal
                    await asyncio.sleep(interval_days * 86400)  # days to seconds
                    
                    # Check if certificate needs renewal
                    if self.lifecycle_manager.should_renew_certificate():
                        logger.info(f"Certificate for {self.lifecycle_manager.did} needs renewal")
                        await self.lifecycle_manager.request_certificate()
                        await self.verification_manager.verify_certificate(self.lifecycle_manager.cert_path)
                        logger.info(f"Certificate for {self.lifecycle_manager.did} renewed successfully")
                        
                except Exception as e:
                    logger.error(f"Error in certificate renewal task: {str(e)}")
                    # Sleep for a shorter time before retrying
                    await asyncio.sleep(3600)  # 1 hour
        
        # Start the task
        self._renewal_task = asyncio.create_task(renewal_task())
        logger.info(f"Started certificate renewal task, checking every {interval_days} days")
        
    async def stop_renewal_task(self) -> None:
        """Stop the certificate renewal task.
        
        Returns:
            None
        """
        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
            logger.info("Certificate renewal task stopped")

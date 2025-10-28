# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Payment endpoints for x402 payment flow.

Provides REST API endpoints for payment session management:
- POST /api/start-payment-session: Start a new payment session
- GET /payment-capture: Browser page to capture payment
- GET /api/payment-status/{session_id}: Get payment status and token
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from x402.encoding import safe_base64_decode
from x402.paywall import get_paywall_html
from x402.types import PaymentPayload

from bindu.utils.logging import get_logger
from .payment_session_manager import PaymentSessionManager

if TYPE_CHECKING:
    from bindu.extensions.x402 import X402AgentExtension
    from x402.types import PaywallConfig, PaymentRequirements

logger = get_logger("bindu.server.middleware.x402.payment_endpoints")


class StartSessionResponse(BaseModel):
    """Response for start payment session."""
    session_id: str
    browser_url: str
    expires_at: str
    status: str


class PaymentStatusResponse(BaseModel):
    """Response for payment status."""
    session_id: str
    status: str
    payment_token: Optional[str] = None
    error: Optional[str] = None


def create_payment_router(
    x402_ext: X402AgentExtension,
    payment_requirements: list[PaymentRequirements],
    paywall_config: PaywallConfig,
    base_url: str = "http://localhost:4021"
) -> tuple[APIRouter, PaymentSessionManager]:
    """Create payment endpoints router.
    
    Args:
        x402_ext: X402 extension instance
        payment_requirements: Payment requirements for the agent
        paywall_config: Paywall configuration
        base_url: Base URL for the server (used to construct browser_url)
        
    Returns:
        Tuple of (APIRouter, PaymentSessionManager)
    """
    router = APIRouter()
    session_manager = PaymentSessionManager()
    
    @router.post("/api/start-payment-session", response_model=StartSessionResponse)
    async def start_payment_session() -> StartSessionResponse:
        """Start a new payment session.
        
        Returns:
            Session details including browser_url to complete payment
        """
        session = session_manager.create_session()
        
        browser_url = f"{base_url}/payment-capture?session_id={session.session_id}"
        
        return StartSessionResponse(
            session_id=session.session_id,
            browser_url=browser_url,
            expires_at=session.expires_at.isoformat(),
            status=session.status
        )
    
    @router.get("/payment-capture", response_class=HTMLResponse)
    async def payment_capture_page(
        request: Request,
        session_id: str = Query(..., description="Payment session ID")
    ) -> HTMLResponse:
        """Browser page to capture payment.
        
        Shows paywall UI and captures payment token when completed.
        
        Args:
            session_id: Payment session ID
            
        Returns:
            HTML page with paywall or success message
        """
        # Verify session exists
        session = session_manager.get_session(session_id)
        if session is None:
            return HTMLResponse(
                content=_get_error_html("Session not found or expired"),
                status_code=404
            )
        
        # Check if payment already completed
        if session.is_completed():
            return HTMLResponse(
                content=_get_success_html(session_id),
                status_code=200
            )
        
        # Check for X-PAYMENT header (payment completed)
        payment_header = request.headers.get("X-PAYMENT", "")
        
        if payment_header:
            # Payment completed - capture token
            try:
                payment_dict = json.loads(safe_base64_decode(payment_header))
                payment_payload = PaymentPayload(**payment_dict)
                
                # Store payment in session (NOT consumed yet!)
                session_manager.complete_session(session_id, payment_payload)
                
                logger.info(f"Payment captured for session: {session_id}")
                
                return HTMLResponse(
                    content=_get_success_html(session_id),
                    status_code=200
                )
                
            except Exception as e:
                error_msg = f"Invalid payment: {str(e)}"
                logger.error(f"Payment capture error for session {session_id}: {e}", exc_info=True)
                session_manager.fail_session(session_id, error_msg)
                
                return HTMLResponse(
                    content=_get_error_html(error_msg),
                    status_code=400
                )
        
        # No payment yet - show paywall
        html_content = get_paywall_html(
            error="Complete payment to continue",
            payment_requirements=payment_requirements,
            paywall_config=paywall_config
        )
        
        return HTMLResponse(
            content=html_content,
            status_code=402
        )
    
    @router.get("/api/payment-status/{session_id}", response_model=PaymentStatusResponse)
    async def get_payment_status(
        session_id: str,
        wait: bool = Query(False, description="Wait for payment completion")
    ) -> PaymentStatusResponse:
        """Get payment status and token.
        
        The payment token is returned but NOT consumed - it can be used
        for the actual API call.
        
        Args:
            session_id: Payment session ID
            wait: If true, wait up to 5 minutes for payment completion
            
        Returns:
            Payment status and token (if completed)
        """
        if wait:
            # Wait for completion (up to 5 minutes)
            session = await session_manager.wait_for_completion(session_id, timeout_seconds=300)
        else:
            # Get current status
            session = session_manager.get_session(session_id)
        
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )
        
        # Prepare response
        response = PaymentStatusResponse(
            session_id=session.session_id,
            status=session.status,
            error=session.error
        )
        
        # Include payment token if completed (but don't consume it!)
        if session.is_completed() and session.payment_payload:
            # Return the payment payload as base64-encoded JSON
            # This can be used directly as X-PAYMENT header
            import base64
            payment_json = session.payment_payload.model_dump_json(by_alias=True)
            payment_token = base64.b64encode(payment_json.encode("utf-8")).decode("utf-8")
            response.payment_token = payment_token
        
        return response
    
    return router, session_manager


def _get_success_html(session_id: str) -> str:
    """Generate success HTML page."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 1rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
            }}
            .success-icon {{
                width: 80px;
                height: 80px;
                margin: 0 auto 1.5rem;
                background: #10b981;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 3rem;
            }}
            h1 {{
                color: #1f2937;
                margin: 0 0 1rem;
                font-size: 2rem;
            }}
            p {{
                color: #6b7280;
                margin: 0 0 2rem;
                font-size: 1.1rem;
            }}
            .session-id {{
                background: #f3f4f6;
                padding: 1rem;
                border-radius: 0.5rem;
                font-family: monospace;
                font-size: 0.9rem;
                word-break: break-all;
                color: #374151;
            }}
            .note {{
                margin-top: 2rem;
                padding: 1rem;
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                border-radius: 0.5rem;
                text-align: left;
                font-size: 0.9rem;
                color: #92400e;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✓</div>
            <h1>Payment Successful!</h1>
            <p>Your payment has been captured and is ready to use.</p>
            <div class="session-id">
                Session ID: {session_id}
            </div>
            <div class="note">
                <strong>Note:</strong> Your payment token has been captured but not consumed yet. 
                You can now retrieve it using the API and use it for your request.
            </div>
        </div>
    </body>
    </html>
    """


def _get_error_html(error: str) -> str:
    """Generate error HTML page."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Error</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #f87171 0%, #dc2626 100%);
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 1rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
            }}
            .error-icon {{
                width: 80px;
                height: 80px;
                margin: 0 auto 1.5rem;
                background: #ef4444;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 3rem;
                color: white;
            }}
            h1 {{
                color: #1f2937;
                margin: 0 0 1rem;
                font-size: 2rem;
            }}
            p {{
                color: #6b7280;
                margin: 0;
                font-size: 1.1rem;
            }}
            .error-message {{
                margin-top: 1.5rem;
                padding: 1rem;
                background: #fee2e2;
                border-left: 4px solid #dc2626;
                border-radius: 0.5rem;
                text-align: left;
                font-size: 0.9rem;
                color: #991b1b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">✕</div>
            <h1>Payment Error</h1>
            <p>There was a problem with your payment.</p>
            <div class="error-message">
                {error}
            </div>
        </div>
    </body>
    </html>
    """

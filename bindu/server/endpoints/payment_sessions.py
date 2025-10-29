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

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from x402.encoding import safe_base64_decode
from x402.paywall import get_paywall_html
from x402.types import PaymentPayload

from bindu.utils.logging import get_logger
from bindu.utils.request_utils import handle_endpoint_errors

logger = get_logger("bindu.server.endpoints.payment_sessions")


@handle_endpoint_errors("start payment session")
async def start_payment_session_endpoint(
    app: BinduApplication, request: Request
) -> Response:
    """Start a new payment session.

    Returns:
        Session details including browser_url to complete payment
    """
    if not app._payment_session_manager:
        return JSONResponse(
            content={"error": "Payment sessions not enabled"}, status_code=503
        )

    session = app._payment_session_manager.create_session()

    # Construct browser URL using app's base URL
    browser_url = f"{app.manifest.url}/payment-capture?session_id={session.session_id}"

    return JSONResponse(
        content={
            "session_id": session.session_id,
            "browser_url": browser_url,
            "expires_at": session.expires_at.isoformat(),
            "status": session.status,
        }
    )


@handle_endpoint_errors("payment capture")
async def payment_capture_endpoint(
    app: BinduApplication, request: Request
) -> Response:
    """Browser page to capture payment.

    Shows paywall UI and captures payment token when completed.
    """
    if not app._payment_session_manager:
        return HTMLResponse(
            content=_get_error_html("Payment sessions not enabled"), status_code=503
        )

    session_id = request.query_params.get("session_id")
    if not session_id:
        return HTMLResponse(
            content=_get_error_html("Session ID required"), status_code=400
        )

    # Verify session exists
    session = app._payment_session_manager.get_session(session_id)
    if session is None:
        return HTMLResponse(
            content=_get_error_html("Session not found or expired"), status_code=404
        )

    # Check if payment already completed
    if session.is_completed():
        return HTMLResponse(content=_get_success_html(session_id), status_code=200)

    # Check for payment token (from header or query param)
    payment_token = request.headers.get("X-PAYMENT", "") or request.query_params.get(
        "payment", ""
    )

    if payment_token:
        # Payment completed - capture token
        try:
            payment_dict = json.loads(safe_base64_decode(payment_token))
            payment_payload = PaymentPayload.model_validate(payment_dict)

            # Store payment in session (NOT consumed yet!)
            app._payment_session_manager.complete_session(session_id, payment_payload)

            logger.info(f"Payment captured for session: {session_id}")

            return HTMLResponse(content=_get_success_html(session_id), status_code=200)

        except Exception as e:
            error_msg = f"Invalid payment: {str(e)}"
            logger.error(
                f"Payment capture error for session {session_id}: {e}", exc_info=True
            )
            app._payment_session_manager.fail_session(session_id, error_msg)

            return HTMLResponse(content=_get_error_html(error_msg), status_code=400)

    # No payment yet - show paywall
    if not app._payment_requirements or not app._paywall_config:
        return HTMLResponse(
            content=_get_error_html("Payment configuration not available"),
            status_code=503,
        )

    # Add session_id to resource URL

    payment_reqs_with_session = []
    for req in app._payment_requirements:
        # Append session_id to resource URL using model_copy
        updated_req = req.model_copy(
            update={"resource": f"{req.resource}?session_id={session_id}"}
        )
        payment_reqs_with_session.append(updated_req)

    html_content = get_paywall_html(
        error="Complete payment to continue",
        payment_requirements=payment_reqs_with_session,
        paywall_config=app._paywall_config,
    )

    return HTMLResponse(content=html_content, status_code=402)


@handle_endpoint_errors("payment status")
async def payment_status_endpoint(
    app: BinduApplication, request: Request
) -> Response:
    """Get payment status and token.

    The payment token is returned but NOT consumed - it can be used
    for the actual API call.
    """
    if not app._payment_session_manager:
        return JSONResponse(
            content={"error": "Payment sessions not enabled"}, status_code=503
        )

    session_id = request.path_params.get("session_id")
    if not session_id:
        return JSONResponse(content={"error": "Session ID required"}, status_code=400)

    wait = request.query_params.get("wait", "false").lower() == "true"

    if wait:
        # Wait for completion (up to 5 minutes)
        session = await app._payment_session_manager.wait_for_completion(
            session_id, timeout_seconds=300
        )
    else:
        # Get current status
        session = app._payment_session_manager.get_session(session_id)

    if session is None:
        return JSONResponse(
            content={"error": "Session not found or expired"}, status_code=404
        )

    # Prepare response
    response_data = {
        "session_id": session.session_id,
        "status": session.status,
    }

    if session.error:
        response_data["error"] = session.error

    # Include payment token if completed (but don't consume it!)
    if session.is_completed() and session.payment_payload:
        # Return the payment payload as base64-encoded JSON
        # This can be used directly as X-PAYMENT header
        import base64

        payment_json = session.payment_payload.model_dump_json(by_alias=True)
        payment_token = base64.b64encode(payment_json.encode("utf-8")).decode("utf-8")
        response_data["payment_token"] = payment_token

    return JSONResponse(content=response_data)


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

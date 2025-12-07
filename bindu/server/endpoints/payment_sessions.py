# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
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

from bindu.server.applications import BinduApplication
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

    # Ensure manifest exists
    if app.manifest is None:
        return JSONResponse(
            content={"error": "Agent manifest not configured"}, status_code=500
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
async def payment_capture_endpoint(app: BinduApplication, request: Request) -> Response:
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
async def payment_status_endpoint(app: BinduApplication, request: Request) -> Response:
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


def _get_common_styles() -> str:
    """Generate common CSS styles for payment pages."""
    return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            background: white;
            padding: 3rem;
            border-radius: 1rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .icon {
            width: 80px;
            height: 80px;
            margin: 0 auto 1.5rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
        }
        h1 {
            color: #1f2937;
            margin: 0 0 1rem;
            font-size: 2rem;
        }
        p {
            color: #6b7280;
            margin: 0 0 2rem;
            font-size: 1.1rem;
        }
    """


def _get_base_html(
    title: str, background_gradient: str, body_content: str, additional_styles: str = ""
) -> str:
    """Generate base HTML structure for payment pages.

    Args:
        title: Page title
        background_gradient: CSS gradient for body background
        body_content: HTML content for the page body
        additional_styles: Additional CSS styles specific to the page
    """
    common_styles = _get_common_styles()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            {common_styles}
            body {{
                background: {background_gradient};
            }}
            {additional_styles}
        </style>
    </head>
    <body>
        {body_content}
    </body>
    </html>
    """


def _get_success_html(session_id: str) -> str:
    """Generate success HTML page with copy button."""
    additional_styles = """
        .icon {
            background: #10b981;
        }
        .session-id-container {
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
        }
        .session-id {
            font-family: monospace;
            font-size: 0.9rem;
            word-break: break-all;
            color: #374151;
            flex: 1;
            text-align: left;
        }
        .copy-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .copy-btn:hover {
            background: #5568d3;
            transform: translateY(-1px);
        }
        .copy-btn:active {
            transform: translateY(0);
        }
        .copy-btn.copied {
            background: #10b981;
        }
        .note {
            margin-top: 2rem;
            padding: 1rem;
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            border-radius: 0.5rem;
            text-align: left;
            font-size: 0.9rem;
            color: #92400e;
        }
    """

    body_content = f"""
        <div class="container">
            <div class="icon">✓</div>
            <h1>Payment Successful!</h1>
            <p>Your payment has been captured and is ready to use.</p>
            <div class="session-id-container">
                <div class="session-id" id="session-id-text">
                    Session ID: {session_id}
                </div>
                <button class="copy-btn" id="copy-btn" onclick="copySessionId()">
                    Copy
                </button>
            </div>
            <div class="note">
                <strong>Note:</strong> Your payment token has been captured but not consumed yet.
                You can now retrieve it using the API and use it for your request.
            </div>
        </div>
        <script>
            function copySessionId() {{
                const sessionId = '{session_id}';
                const btn = document.getElementById('copy-btn');

                navigator.clipboard.writeText(sessionId).then(() => {{
                    // Success feedback
                    btn.textContent = 'Copied!';
                    btn.classList.add('copied');

                    // Reset after 2 seconds
                    setTimeout(() => {{
                        btn.textContent = 'Copy';
                        btn.classList.remove('copied');
                    }}, 2000);
                }}).catch(err => {{
                    // Fallback for older browsers
                    console.error('Failed to copy:', err);
                    btn.textContent = 'Error';
                    setTimeout(() => {{
                        btn.textContent = 'Copy';
                    }}, 2000);
                }});
            }}
        </script>
    """

    return _get_base_html(
        title="Payment Successful",
        background_gradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        body_content=body_content,
        additional_styles=additional_styles,
    )


def _get_error_html(error: str) -> str:
    """Generate error HTML page."""
    additional_styles = """
        .icon {
            background: #ef4444;
            color: white;
        }
        p {
            margin: 0;
        }
        .error-message {
            margin-top: 1.5rem;
            padding: 1rem;
            background: #fee2e2;
            border-left: 4px solid #dc2626;
            border-radius: 0.5rem;
            text-align: left;
            font-size: 0.9rem;
            color: #991b1b;
        }
    """

    body_content = f"""
        <div class="container">
            <div class="icon">✕</div>
            <h1>Payment Error</h1>
            <p>There was a problem with your payment.</p>
            <div class="error-message">
                {error}
            </div>
        </div>
    """

    return _get_base_html(
        title="Payment Error",
        background_gradient="linear-gradient(135deg, #f87171 0%, #dc2626 100%)",
        body_content=body_content,
        additional_styles=additional_styles,
    )

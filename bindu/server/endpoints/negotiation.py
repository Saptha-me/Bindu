# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Negotiation endpoint for capability assessment.

This endpoint evaluates how well the agent can handle a task
based on skills, performance, load, and pricing constraints.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)
from bindu.server.applications import BinduApplication
from bindu.server.negotiation.capability_calculator import (
    CapabilityCalculator,
    ScoringWeights,
)
from bindu.utils.request_utils import handle_endpoint_errors, get_client_ip
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.endpoints.negotiation")


@handle_endpoint_errors("task assessment")
async def negotiation_endpoint(app: BinduApplication, request: Request) -> Response:
    """Assess agent's capability to handle a task.

    Evaluates skill match, IO compatibility, performance, load, and cost
    to produce an acceptance decision with confidence and detailed scoring.
    """
    client_ip = get_client_ip(request)
    logger.debug(f"Negotiation request from {client_ip}")

    # Ensure manifest exists
    if app.manifest is None:
        return JSONResponse(
            content={"error": "Agent manifest not configured"}, status_code=500
        )

    # Parse request body
    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"Invalid JSON in negotiation request: {e}")
        return JSONResponse(
            content={"error": "Invalid JSON payload"}, status_code=400
        )

    # Extract required field
    task_summary = body.get("task_summary")
    if not task_summary:
        return JSONResponse(
            content={"error": "'task_summary' is required"}, status_code=400
        )

    # Extract optional fields
    task_details = body.get("task_details")
    input_mime_types = body.get("input_mime_types")
    output_mime_types = body.get("output_mime_types")
    max_latency_ms = body.get("max_latency_ms")
    max_cost_amount = body.get("max_cost_amount")
    required_tools = body.get("required_tools")
    forbidden_tools = body.get("forbidden_tools")
    min_score = body.get("min_score", 0.0)

    # Extract custom weights if provided
    weights = None
    if "weights" in body:
        w = body["weights"]
        try:
            weights = ScoringWeights(
                skill_match=w.get("skill_match", 0.55),
                io_compatibility=w.get("io_compatibility", 0.20),
                performance=w.get("performance", 0.15),
                load=w.get("load", 0.05),
                cost=w.get("cost", 0.05),
            )
        except ValueError as e:
            return JSONResponse(
                content={"error": f"Invalid weights: {e}"}, status_code=400
            )

    # Get queue depth from scheduler if available
    queue_depth = None
    if app.scheduler and hasattr(app.scheduler, "get_queue_length"):
        try:
            queue_depth = await app.scheduler.get_queue_length()
        except Exception as e:
            logger.warning(f"Failed to get queue depth: {e}")

    # Get x402 extension if available
    x402_extension = None
    if app.manifest.x402:
        x402_extension = app.manifest.x402

    # Initialize calculator
    skills = app.manifest.skills or []
    calculator = CapabilityCalculator(skills=skills, x402_extension=x402_extension)

    # Run calculation
    result = calculator.calculate(
        task_summary=task_summary,
        task_details=task_details,
        input_mime_types=input_mime_types,
        output_mime_types=output_mime_types,
        max_latency_ms=max_latency_ms,
        max_cost_amount=max_cost_amount,
        required_tools=required_tools,
        forbidden_tools=forbidden_tools,
        queue_depth=queue_depth,
        weights=weights,
        min_score=min_score,
    )

    # Format response
    response_data = {
        "accepted": result.accepted,
        "score": result.score,
        "confidence": result.confidence,
    }

    if result.rejection_reason:
        response_data["rejection_reason"] = result.rejection_reason

    if result.skill_matches:
        response_data["skill_matches"] = [
            {
                "skill_id": m.skill_id,
                "skill_name": m.skill_name,
                "score": m.score,
                "reasons": m.reasons,
            }
            for m in result.skill_matches
        ]

    if result.matched_tags:
        response_data["matched_tags"] = result.matched_tags

    if result.matched_capabilities:
        response_data["matched_capabilities"] = result.matched_capabilities

    if result.latency_estimate_ms is not None:
        response_data["latency_estimate_ms"] = result.latency_estimate_ms

    if result.queue_depth is not None:
        response_data["queue_depth"] = result.queue_depth

    if result.subscores:
        response_data["subscores"] = result.subscores

    logger.info(
        f"Assessment for '{task_summary[:50]}...': "
        f"accepted={result.accepted}, score={result.score}, "
        f"confidence={result.confidence}"
    )

    resp = JSONResponse(content=response_data)
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp

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
from bindu.utils.capabilities import get_x402_extension_from_capabilities
from bindu.settings import app_settings

logger = get_logger("bindu.server.endpoints.negotiation")


def _get_or_create_calculator(app: BinduApplication) -> CapabilityCalculator:
    """Get or create cached calculator instance.

    Caches calculator in app instance to avoid repeated initialization.
    Invalidates cache if manifest changes.
    """
    # Check if calculator exists and manifest hasn't changed
    if (
        hasattr(app, "_negotiation_calculator")
        and hasattr(app, "_negotiation_calculator_manifest_id")
        and app._negotiation_calculator_manifest_id == id(app.manifest)
    ):
        return app._negotiation_calculator  # type: ignore[return-value]

    # Create new calculator
    skills = app.manifest.skills or [] if app.manifest else []
    x402_extension = (
        get_x402_extension_from_capabilities(app.manifest) if app.manifest else None
    )

    # Get embedding API key from manifest negotiation config if available
    embedding_api_key = None
    if (
        app.manifest
        and hasattr(app.manifest, "negotiation")
        and app.manifest.negotiation
    ):
        embedding_api_key = app.manifest.negotiation.get("embedding_api_key")

    calculator = CapabilityCalculator(
        skills=skills,
        x402_extension=x402_extension,
        embedding_api_key=embedding_api_key,
    )

    # Cache calculator and manifest ID
    app._negotiation_calculator = calculator  # type: ignore[attr-defined]
    app._negotiation_calculator_manifest_id = id(app.manifest)  # type: ignore[attr-defined]

    logger.debug("Created and cached new CapabilityCalculator instance")
    return calculator


@handle_endpoint_errors("task assessment")
async def negotiation_endpoint(app: BinduApplication, request: Request) -> Response:
    """Assess agent's capability to handle a task.

    Evaluates skill match, IO compatibility, performance, load, and cost
    to produce an acceptance decision with confidence and detailed scoring.
    """
    client_ip = get_client_ip(request)
    logger.debug(f"Negotiation request from {client_ip}")

    # Early validation: manifest exists
    if app.manifest is None:
        return JSONResponse(
            content={"error": "Agent manifest not configured"}, status_code=500
        )

    # Early validation: parse request body
    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"Invalid JSON in negotiation request: {e}")
        return JSONResponse(content={"error": "Invalid JSON payload"}, status_code=400)

    # Early validation: required field
    task_summary = body.get("task_summary")
    if not task_summary:
        return JSONResponse(
            content={"error": "'task_summary' is required"}, status_code=400
        )

    # Early validation: task_summary length
    if len(task_summary) > 10000:
        return JSONResponse(
            content={
                "error": "task_summary exceeds maximum length of 10000 characters"
            },
            status_code=400,
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

    # Get queue depth by counting non-terminal tasks from storage
    queue_depth = None
    if app.task_manager and app.task_manager.storage:
        try:
            tasks = await app.task_manager.storage.list_tasks()
            # Count tasks in non-terminal states (from agent settings)
            queue_depth = sum(
                1
                for task in tasks
                if task.get("state") in app_settings.agent.non_terminal_states
            )
        except Exception as e:
            logger.warning(f"Failed to get queue depth from storage: {e}")

    # Get or create cached calculator instance
    calculator = _get_or_create_calculator(app)

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

    # Format response (optimized with dict comprehension)
    response_data = {
        "accepted": result.accepted,
        "score": result.score,
        "confidence": result.confidence,
        **(
            {"rejection_reason": result.rejection_reason}
            if result.rejection_reason
            else {}
        ),
        **(
            {
                "skill_matches": [
                    {
                        "skill_id": m.skill_id,
                        "skill_name": m.skill_name,
                        "score": m.score,
                        "reasons": m.reasons,
                    }
                    for m in result.skill_matches
                ]
            }
            if result.skill_matches
            else {}
        ),
        **({"matched_tags": result.matched_tags} if result.matched_tags else {}),
        **(
            {"matched_capabilities": result.matched_capabilities}
            if result.matched_capabilities
            else {}
        ),
        **(
            {"latency_estimate_ms": result.latency_estimate_ms}
            if result.latency_estimate_ms is not None
            else {}
        ),
        **(
            {"queue_depth": result.queue_depth}
            if result.queue_depth is not None
            else {}
        ),
        **({"subscores": result.subscores} if result.subscores else {}),
    }

    logger.info(
        f"Assessment for '{task_summary[:50]}...': "
        f"accepted={result.accepted}, score={result.score}, "
        f"confidence={result.confidence}"
    )

    resp = JSONResponse(content=response_data)
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp

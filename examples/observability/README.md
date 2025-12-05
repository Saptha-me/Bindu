\# Observability: Structured Logging + Request Metrics



This example shows how to enable \*\*structured (JSON) logs\*\*, \*\*request timing\*\*, and \*\*correlated request IDs\*\* for the Bindu server (Starlette/FastAPI) using \*\*Loguru\*\*.



\## What you get



\- JSON logs (toggleable)

\- Millisecond latency per request

\- Per-request `request\_id` propagated through all logs

\- Uvicorn + stdlib logs merged into the same format



\## Quick start (local dev)



1\) Ensure dependencies are installed (Loguru is already in the project):



```bash

uv sync --dev



In the module where you create your Starlette/FastAPI app (e.g. the Bindu app factory), add:



from examples.observability.logging\_config import setup\_logging, instrument\_starlette



\# 1) Configure logging ONCE at startup

setup\_logging(level="INFO", json\_logs=True)



\# 2) After you create the app instance:

\# app = <your Starlette/FastAPI/Bindu app>

instrument\_starlette(app)





Run the server:



uvicorn your.module:app --reload --host 127.0.0.1 --port 8000





Make a request and observe logs:



curl -i http://127.0.0.1:8000/health





You’ll see JSON output like:



{

&nbsp; "time": "2025-12-04T18:45:32.812345+00:00",

&nbsp; "level": "INFO",

&nbsp; "message": "HTTP GET /health -> 200 in 3.42 ms",

&nbsp; "request\_id": "7c2a9b64-4b66-4cce-9d12-1c7e34b7c0b9"

}





The response will include a X-Request-ID header you can use to correlate client logs with server logs.



Tuning



setup\_logging(level="DEBUG", json\_logs=False) to switch to human-readable logs.



To reuse an incoming request id from clients, send the header X-Request-ID: <uuid>.



Middleware options (see source):



get\_request\_id\_header (default: X-Request-ID)



response\_request\_id\_header (default: X-Request-ID)



sample to reduce log volume if needed.



Why this helps



Ops-friendly: machine-parseable logs for ELK, Loki, or CloudWatch Logs Insights.



Debuggable: one request\_id stitched across Uvicorn, your code, and async tasks.



Measurable: latency in ms for every route.





---



\# 3) PR Message (ready to paste)



\*\*Title\*\*





feat: add structured logging example for observability





\*\*Description\*\*





This PR adds an observability example that enables structured (JSON) logs,

request timing in ms, and per-request correlation IDs for the Bindu server.



What’s included:



examples/observability/logging\_config.py:



Loguru configuration (single sink, JSON toggle)



Stdlib/Uvicorn log interception



Starlette middleware to inject request\_id and log per-request latency



examples/observability/README.md: setup \& usage guide



Benefits:



Production-friendly, machine-parsable logs for ELK/Loki/CloudWatch



Consistent format across Uvicorn + application logs



Easier debugging and metrics via request\_id + latency



No core code changes required. Fully optional and opt-in for contributors/users.





---

from collections import defaultdict
from threading import Lock


class AgentHealthRegistry:
    def __init__(self):
        self._lock = Lock()
        self._stats = defaultdict(lambda: {
            "calls": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        })

    def record(self, agent_id: str, latency: float, success: bool):
        with self._lock:
            self._stats[agent_id]["calls"] += 1
            if not success:
                self._stats[agent_id]["errors"] += 1
            self._stats[agent_id]["total_latency_ms"] += latency

    def get_stats(self):
        with self._lock:
            result = {}
            for agent_id, data in self._stats.items():
                calls = data["calls"]
                errors = data["errors"]
                total_latency = data["total_latency_ms"]

                avg_latency = total_latency / calls if calls > 0 else 0
                error_rate = errors / calls if calls > 0 else 0

                health_score = max(0, 1 - error_rate)

                # Intelligent classification
                status = "healthy"

                if calls >= 5:
                    if error_rate > 0.2:
                        status = "unhealthy"
                    elif avg_latency > 500:
                        status = "degraded"

                result[agent_id] = {
                    "calls": calls,
                    "errors": errors,
                    "avg_latency_ms": round(avg_latency, 2),
                    "health_score": round(health_score, 2),
                    "status": status,
                }

            return result


agent_health_registry = AgentHealthRegistry()
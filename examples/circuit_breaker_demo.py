#!/usr/bin/env python3
"""Circuit Breaker Demo — Manual verification of the implementation.

This script demonstrates the circuit breaker pattern in action:
1. CLOSED state: Normal operation, failures tracked
2. OPEN state: Fail-fast when threshold reached
3. HALF_OPEN state: Recovery testing after timeout
4. Back to CLOSED: Circuit recovers after successful call

Run:
    python examples/circuit_breaker_demo.py

Expected Output:
    Shows state transitions as failures accumulate and recovery occurs.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from bindu.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    get_circuit_breaker_stats,
)


async def unreliable_service(should_fail: bool = False) -> str:
    """Simulates an unreliable external service."""
    await asyncio.sleep(0.05)  # Simulate network latency
    if should_fail:
        raise ConnectionError("Service unavailable")
    return "Success!"


async def demo_basic_flow():
    """Demonstrate basic circuit breaker flow."""
    print("\n" + "=" * 60)
    print("CIRCUIT BREAKER DEMO")
    print("=" * 60)

    # Create a circuit breaker with low threshold for demo
    breaker = CircuitBreaker(
        name="demo_service",
        failure_threshold=3,  # Opens after 3 failures
        recovery_timeout=2.0,  # Try recovery after 2 seconds
    )

    print(f"\n📊 Initial State: {breaker.state.value}")
    print(f"   Failure Threshold: {breaker.failure_threshold}")
    print(f"   Recovery Timeout: {breaker.recovery_timeout}s")

    # Phase 1: Successful calls (CLOSED state)
    print("\n" + "-" * 40)
    print("Phase 1: Successful calls (circuit CLOSED)")
    print("-" * 40)

    for i in range(2):
        result = await breaker.call(unreliable_service, should_fail=False)
        print(f"  Call {i+1}: {result} | State: {breaker.state.value} | Failures: {breaker.failure_count}")

    # Phase 2: Failing calls (accumulating failures)
    print("\n" + "-" * 40)
    print("Phase 2: Failing calls (accumulating failures)")
    print("-" * 40)

    for i in range(3):
        try:
            await breaker.call(unreliable_service, should_fail=True)
        except ConnectionError:
            print(f"  Call {i+1}: ConnectionError | State: {breaker.state.value} | Failures: {breaker.failure_count}")
        except CircuitBreakerError as e:
            print(f"  Call {i+1}: ⚡ CIRCUIT OPEN - {e.message}")

    # Phase 3: Circuit is OPEN - calls fail fast
    print("\n" + "-" * 40)
    print("Phase 3: Circuit OPEN - calls fail fast")
    print("-" * 40)

    for i in range(2):
        try:
            await breaker.call(unreliable_service, should_fail=False)
            print(f"  Call {i+1}: Unexpected success!")
        except CircuitBreakerError as e:
            print(f"  Call {i+1}: ⚡ REJECTED - {e.message}")

    # Phase 4: Wait for recovery timeout
    print("\n" + "-" * 40)
    print("Phase 4: Waiting for recovery timeout...")
    print("-" * 40)

    await asyncio.sleep(2.5)  # Wait longer than recovery_timeout
    print("  Waited 2.5s, circuit should try HALF_OPEN")

    # Phase 5: Recovery attempt (HALF_OPEN state)
    print("\n" + "-" * 40)
    print("Phase 5: Recovery attempt (HALF_OPEN)")
    print("-" * 40)

    try:
        result = await breaker.call(unreliable_service, should_fail=False)
        print(f"  Recovery call: {result}")
        print(f"  🎉 Circuit RECOVERED! State: {breaker.state.value}")
    except CircuitBreakerError as e:
        print(f"  Recovery failed: {e.message}")

    # Final stats
    print("\n" + "=" * 60)
    print("FINAL STATS")
    print("=" * 60)
    stats = get_circuit_breaker_stats()
    for name, s in stats.items():
        print(f"\n  {name}:")
        print(f"    State: {s['state']}")
        print(f"    Failures: {s['failure_count']}")


async def demo_decorator():
    """Demonstrate decorator pattern."""
    print("\n" + "=" * 60)
    print("DECORATOR DEMO")
    print("=" * 60)

    from bindu.utils.circuit_breaker import circuit_breaker

    @circuit_breaker(name="decorated_service", failure_threshold=2, recovery_timeout=1.0)
    async def my_service(fail: bool = False):
        if fail:
            raise ConnectionError("Oops!")
        return "Decorated success!"

    print("\n  Testing decorated function:")

    # Success
    result = await my_service(fail=False)
    print(f"    Call 1: {result}")

    # Failures
    for i in range(2):
        try:
            await my_service(fail=True)
        except ConnectionError:
            print(f"    Call {i+2}: ConnectionError (counted)")
        except CircuitBreakerError:
            print(f"    Call {i+2}: Circuit OPEN!")

    # Fail fast
    try:
        await my_service(fail=False)
    except CircuitBreakerError:
        print("    Call 4: Rejected (circuit open)")


async def demo_context_manager():
    """Demonstrate context manager pattern."""
    print("\n" + "=" * 60)
    print("CONTEXT MANAGER DEMO")
    print("=" * 60)

    breaker = CircuitBreaker(
        name="context_demo",
        failure_threshold=2,
        recovery_timeout=1.0,
    )

    print("\n  Using 'async with' syntax:")

    # Success
    async with breaker:
        print("    Inside context: doing work...")
    print(f"    After success: State={breaker.state.value}")

    # Failure
    try:
        async with breaker:
            raise RuntimeError("Simulated error")
    except RuntimeError:
        print(f"    After failure: State={breaker.state.value}, Failures={breaker.failure_count}")


async def main():
    """Run all demos."""
    print("\n🔌 Circuit Breaker Pattern Demonstration\n")

    await demo_basic_flow()
    await demo_decorator()
    await demo_context_manager()

    print("\n" + "=" * 60)
    print("✅ All demos completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

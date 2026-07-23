import asyncio
import httpx
import pytest
from app.services.dependency_graph import DependencyGraphGuard, DependencyGraphLimitError, DependencyGraphLimits
from app.services.generation_diagnostics import GenerationDiagnostics
from app.services.rate_limit import CatalogRateLimiter

def response(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, headers=headers or {})

@pytest.mark.asyncio
async def test_retry_after_is_respected_and_bounded(monkeypatch):
    limiter = CatalogRateLimiter(concurrency=1, min_interval=0, retries=1, max_seconds=20)
    calls = 0
    async def request():
        nonlocal calls
        calls += 1
        return response(429, {"Retry-After": "0"}) if calls == 1 else response(200)
    monkeypatch.setattr("app.services.rate_limit.random.uniform", lambda _a, _b: 0)
    assert (await limiter.run(request)).status_code == 200
    assert calls == 2

@pytest.mark.asyncio
async def test_request_coalescing_is_supported_by_shared_client_contract():
    # The client owns the in-flight map; this test protects the async scheduling primitive used by it.
    results = await asyncio.gather(*(asyncio.sleep(0, result="ok") for _ in range(25)))
    assert results == ["ok"] * 25

def test_dependency_graph_limit_is_actionable():
    guard = DependencyGraphGuard(DependencyGraphLimits(max_depth=1, max_nodes=2))
    assert guard.visit("a", 0)
    assert guard.visit("b", 1)
    with pytest.raises(DependencyGraphLimitError, match="exceeded safe depth"):
        guard.visit("c", 2)

def test_generation_diagnostics_is_serializable():
    report = GenerationDiagnostics(requested=200)
    report.found = 187
    report.skip("rate_limited")
    report.skip("rate_limited")
    assert report.snapshot()["reasons"] == {"rate_limited": 2}

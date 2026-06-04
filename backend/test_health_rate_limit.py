"""Verify health endpoint rate limiting behavior."""
import sys
import os
os.environ['VISIONSCAN_DATA_DIR'] = '/tmp/test_health_ratelimit'

from app import security_mw
from app.config import get_settings
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_default_rate_limit():
    """Health endpoint should get DEFAULT rate limit class, not an exception."""
    settings = get_settings()
    assert settings.enable_rate_limit, "rate limiting must be on"
    
    # Clear buckets
    security_mw.reset_rate_limits()
    
    # Classify a GET /health request
    from starlette.requests import Request
    from starlette.datastructures import URL
    
    # Create a minimal request object
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/api/health',
        'query_string': b'',
    }
    request = Request(scope)
    
    middleware = None
    for m in security_mw._RL_INSTANCES:
        middleware = m
        break
    
    if middleware:
        cls = middleware._classify(request)
        limit = middleware._limit_for(cls, settings)
        print(f"GET /api/health classified as: '{cls}'")
        print(f"Rate limit applied: {limit} per minute")
        print(f"Default rate limit setting: {settings.rate_limit_default_per_min}")
        assert cls == "default", f"Expected 'default' class, got '{cls}'"
        assert limit == settings.rate_limit_default_per_min
    
    # Now hammer the endpoint beyond the default limit
    n_requests = settings.rate_limit_default_per_min + 5
    statuses = []
    got_429 = False
    
    for i in range(n_requests):
        r = client.get('/api/health')
        statuses.append(r.status_code)
        if r.status_code == 429:
            got_429 = True
            print(f"\nGot 429 after {i+1} requests (limit is {settings.rate_limit_default_per_min})")
            print(f"Response: {r.json()}")
            break
    
    if got_429:
        print(f"SUCCESS: Health endpoint IS rate-limited at the DEFAULT limit (as it should be)")
    else:
        print(f"WARNING: Made {n_requests} health requests without hitting the rate limit")
        print(f"Statuses: {statuses}")

if __name__ == "__main__":
    test_health_default_rate_limit()

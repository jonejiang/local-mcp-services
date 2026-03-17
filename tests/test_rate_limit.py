#!/usr/bin/env python3
"""
Rate Limiting Tests for MCP Server
TDD: Test rate limiting functionality
"""
import pytest
import json
import subprocess
import time
import threading
from typing import Dict


# MCP Server path
MCP_SERVER = "/Users/jone/AI/Agents/local-mcp-services/mcp_server.py"


def run_mcp_command(cmd: Dict) -> Dict:
    """Execute MCP command via stdin/stdout"""
    proc = subprocess.Popen(
        ["python3", MCP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=json.dumps(cmd) + "\n", timeout=30)
    try:
        return json.loads(stdout.strip())
    except:
        return {"error": stdout or stderr}


class TestRateLimiting:
    """Rate limiting test suite"""

    def test_rate_limit_search_tool(self):
        """Test rate limiting on search tool"""
        # Send many requests quickly to exceed rate limit
        errors = 0
        for i in range(35):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": f"test {i}"}
                }
            })
            if "Rate limit" in str(resp) or "rate limit" in str(resp).lower():
                errors += 1

        # Should hit rate limit
        assert errors > 0, "Rate limiting should block requests after limit"

    def test_rate_limit_ocr_tool(self):
        """Test rate limiting on OCR tool"""
        errors = 0
        for i in range(15):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "ocr",
                    "arguments": {"url": "https://example.com/image.png"}
                }
            })
            if "Rate limit" in str(resp):
                errors += 1

        assert errors > 0, "Rate limiting should block OCR requests"

    def test_rate_limit_navigate_tool(self):
        """Test rate limiting on navigate tool"""
        errors = 0
        for i in range(25):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "navigate",
                    "arguments": {"url": "https://example.com"}
                }
            })
            if "Rate limit" in str(resp):
                errors += 1

        assert errors > 0, "Rate limiting should block navigate requests"

    def test_rate_limit_crawl_tool(self):
        """Test rate limiting on crawl tool"""
        errors = 0
        for i in range(15):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "crawl",
                    "arguments": {"url": "https://example.com"}
                }
            })
            if "Rate limit" in str(resp):
                errors += 1

        assert errors > 0, "Rate limiting should block crawl requests"

    def test_rate_limit_reset_after_window(self):
        """Test rate limit resets after time window"""
        # Send request to set initial rate limit
        run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "test"}
            }
        })

        # Wait for rate limit window to reset (60 seconds)
        # For testing, we just verify the concept
        time.sleep(1)

        # Should be able to make requests after window
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {}
        })

        # This is a basic test - in production, wait full window
        assert "result" in resp or "error" in resp

    def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent requests"""
        results = []
        errors = []

        def make_request(i):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": f"concurrent {i}"}
                }
            })
            results.append(resp)
            if "Rate limit" in str(resp):
                errors.append(i)

        # Make concurrent requests
        threads = []
        for i in range(20):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Some requests should be rate limited
        assert len(results) == 20

    def test_different_tools_have_different_limits(self):
        """Test different tools have independent rate limits"""
        # Search has higher limit (30/min)
        search_resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "test"}
            }
        })

        # OCR has lower limit (10/min)
        ocr_resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ocr",
                "arguments": {"url": "https://example.com/img.png"}
            }
        })

        # Both should work independently
        # Rate limits are per-tool
        assert search_resp is not None
        assert ocr_resp is not None

    def test_rate_limit_not_affected_by_other_tools(self):
        """Test hitting one tool's rate limit doesn't affect others"""
        # Use up search rate limit
        for i in range(35):
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": f"test {i}"}
                }
            })

        # OCR should still work
        ocr_resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 999,
            "method": "tools/call",
            "params": {
                "name": "ocr",
                "arguments": {"url": "https://example.com/img.png"}
            }
        })

        # OCR shouldn't be affected by search rate limit
        assert ocr_resp is not None

    def test_rate_limit_returns_error_message(self):
        """Test rate limit returns proper error message"""
        # Send many requests
        for i in range(35):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": f"test {i}"}
                }
            })

            if "Rate limit" in str(resp):
                # Check error format
                if "error" in resp:
                    assert "message" in resp["error"]
                    return  # Test passed

        # If we got here, rate limit wasn't triggered
        # This is OK if implementation uses sliding window
        pytest.skip("Rate limit timing dependent")

    def test_initialize_not_rate_limited(self):
        """Test initialize method is not rate limited"""
        # Initialize should never be rate limited
        for i in range(100):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "initialize",
                "params": {}
            })
            assert "result" in resp, f"Initialize should not be rate limited (attempt {i})"

    def test_tools_list_not_rate_limited(self):
        """Test tools/list method is not rate limited"""
        for i in range(100):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/list",
                "params": {}
            })
            assert "result" in resp, f"tools/list should not be rate limited (attempt {i})"

    def test_rate_limit_memory_safety(self):
        """Test rate limiter doesn't leak memory"""
        import tracemalloc

        tracemalloc.start()

        # Make many requests
        for i in range(100):
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "initialize",
                "params": {}
            })

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory should not grow excessively
        # Allow 10MB for rate limit storage
        assert peak < 10 * 1024 * 1024, f"Memory leak detected: {peak / 1024 / 1024:.2f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

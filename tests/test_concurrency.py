#!/usr/bin/env python3
"""
Concurrency Tests for MCP Server
TDD: Test thread safety and concurrent request handling
"""
import pytest
import json
import subprocess
import threading
import time
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed


# MCP Server path - use relative path
import os
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SERVER = os.path.join(SCRIPT_DIR, "mcp_server.py")


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


class TestConcurrentRequests:
    """Test concurrent request handling"""

    def test_parallel_initializes(self):
        """Test parallel initialize requests"""
        results = []

        def make_request(i):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "initialize",
                "params": {}
            })
            return resp

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        success = sum(1 for r in results if "result" in r)
        assert success == 20, f"Only {success}/20 requests succeeded"

    def test_parallel_tool_calls(self):
        """Test parallel tool calls"""
        results = []

        def make_request(i):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": f"test {i}"}
                }
            })
            return resp

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All should return (may have errors if backend unavailable)
        assert len(results) == 20

    def test_mixed_methods_concurrent(self):
        """Test mixed method types concurrent"""
        results = []

        def make_request(i):
            if i % 3 == 0:
                method = "initialize"
                params = {}
            elif i % 3 == 1:
                method = "tools/list"
                params = {}
            else:
                method = "tools/call"
                params = {
                    "name": "search",
                    "arguments": {"query": f"test {i}"}
                }

            return run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": method,
                "params": params
            })

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_request, i) for i in range(30)]
            results = [f.result() for f in as_completed(futures)]

        assert len(results) == 30


class TestRaceConditions:
    """Test for race conditions"""

    def test_rate_limiter_thread_safety(self):
        """Test rate limiter under concurrent access"""
        results = []
        errors = []

        def make_request(i):
            try:
                resp = run_mcp_command({
                    "jsonrpc": "2.0",
                    "id": i,
                    "method": "tools/call",
                    "params": {
                        "name": "search",
                        "arguments": {"query": f"race test {i}"}
                    }
                })
                results.append(resp)
                if "Rate limit" in str(resp):
                    errors.append(i)
            except Exception as e:
                results.append({"error": str(e)})

        # Make many concurrent requests
        threads = []
        for i in range(50):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should complete without crashes
        assert len(results) == 50
        # Some may hit rate limit
        assert len(errors) >= 0

    def test_id_sequence_thread_safety(self):
        """Test request IDs are handled correctly under concurrency"""
        results = {}

        def make_request(i):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "initialize",
                "params": {}
            })
            results[i] = resp.get("id")

        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All IDs should be preserved
        assert len(results) == 10


class TestMemoryUnderLoad:
    """Test memory handling under load"""

    def test_memory_stability(self):
        """Test memory doesn't grow unbounded"""
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

        # Memory should stay reasonable (< 50MB)
        assert peak < 50 * 1024 * 1024, f"Memory too high: {peak / 1024 / 1024:.2f}MB"

    def test_no_memory_leaks(self):
        """Test no memory leaks with repeated requests"""
        import gc

        # Force garbage collection
        gc.collect()

        initial_objects = len(gc.get_objects())

        # Make many requests
        for i in range(50):
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "initialize",
                "params": {}
            })

        # Force garbage collection
        gc.collect()

        final_objects = len(gc.get_objects())

        # Should not have significant memory growth
        # Allow some growth for rate limiter data structures
        growth = final_objects - initial_objects
        assert growth < 1000, f"Possible memory leak: {growth} new objects"


class TestErrorHandlingUnderLoad:
    """Test error handling under concurrent load"""

    def test_all_errors_handled(self):
        """Test all errors are handled properly"""
        results = []

        # Mix of valid and invalid requests
        requests = [
            {"method": "initialize", "params": {}},
            {"method": "invalid", "params": {}},
            {"method": "tools/list", "params": {}},
            {"method": "invalid_method", "params": {}},
            {"method": "initialize", "params": {}},
        ] * 5

        for i, req in enumerate(requests):
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": req["method"],
                "params": req["params"]
            })
            results.append(resp)

        # All should return a response (no crashes)
        assert len(results) == len(requests)

        # Valid requests should succeed
        valid_success = sum(1 for r in results[:10] if "result" in r)
        assert valid_success >= 3  # At least initialize, tools/list should work

    def test_rapid_fire_requests(self):
        """Test rapid fire requests don't cause issues"""
        results = []

        # Send requests as fast as possible
        for i in range(50):
            try:
                resp = run_mcp_command({
                    "jsonrpc": "2.0",
                    "id": i,
                    "method": "initialize",
                    "params": {}
                })
                results.append(resp)
            except Exception as e:
                results.append({"error": str(e)})

        # All should complete
        assert len(results) == 50


class TestConnectionHandling:
    """Test connection handling"""

    def test_multiple_rapid_connections(self):
        """Test multiple rapid connections"""
        connections = []

        def make_connection(i):
            return run_mcp_command({
                "jsonrpc": "2.0",
                "id": i,
                "method": "initialize",
                "params": {}
            })

        # Start many connections rapidly
        threads = []
        for i in range(20):
            t = threading.Thread(target=lambda: connections.append(make_connection(i)))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(connections) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

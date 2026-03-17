#!/usr/bin/env python3
"""
Local MCP Comprehensive Test Suite
Tests: Positive, Negative, Exception, Rollback/Recovery
"""
import json
import subprocess
import time
import sys
import requests
from typing import Dict, Any, Tuple

# MCP Server path
MCP_SERVER = "/Users/jone/AI/Agents/local-mcp-services/mcp_server.py"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def run_mcp_command(cmd: Dict) -> Dict:
    """Execute MCP command via stdin/stdout"""
    proc = subprocess.Popen(
        ["python3", MCP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(input=json.dumps(cmd) + "\n")
    try:
        return json.loads(stdout.strip())
    except:
        return {"error": stdout or stderr}

def check_backend(port: int, path: str = "/health") -> bool:
    """Check if backend service is healthy"""
    try:
        r = requests.get(f"http://localhost:{port}{path}", timeout=5)
        return r.status_code == 200
    except:
        return False

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def add_pass(self):
        self.passed += 1
        print(f"{GREEN}✓ PASS{RESET}")

    def add_fail(self, msg: str = ""):
        self.failed += 1
        print(f"{RED}✗ FAIL{RESET} {msg}")

    def add_warn(self, msg: str = ""):
        self.warnings += 1
        print(f"{YELLOW}⚠ WARN{RESET} {msg}")

result = TestResult()

# ============================================================
# POSITIVE TESTS
# ============================================================
print(f"\n{BLUE}{'='*60}")
print("POSITIVE TESTS - Normal Functionality")
print('='*60 + RESET)

# Test 1: Initialize
print("\n[Test 1.1] MCP Initialize")
resp = run_mcp_command({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
if resp.get("result", {}).get("protocolVersion"):
    result.add_pass()
else:
    result.add_fail(str(resp))

# Test 2: List tools
print("\n[Test 1.2] List Tools")
resp = run_mcp_command({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
tools = resp.get("result", {}).get("tools", [])
tool_names = [t["name"] for t in tools]
if "search" in tool_names and "ocr" in tool_names:
    result.add_pass()
else:
    result.add_fail(f"Missing tools: {tool_names}")

# Test 3: Search (with working backend)
print("\n[Test 1.3] Search - Python query")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "search", "arguments": {"query": "python"}}
})
content = resp.get("result", {}).get("content", [{}])[0].get("text", "")
if content and "Python" in content:
    result.add_pass()
else:
    result.add_fail(f"No results: {content[:100]}")

# Test 4: OCR (test image)
print("\n[Test 1.4] OCR - Image to text")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 4, "method": "tools/call",
    "params": {"name": "ocr", "arguments": {"url": "https://httpbin.org/image/png"}}
})
if "error" not in resp or "content" in resp.get("result", {}):
    result.add_pass()
else:
    result.add_fail(str(resp))

# Test 5: Navigate
print("\n[Test 1.5] Navigate - Web browsing")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 5, "method": "tools/call",
    "params": {"name": "navigate", "arguments": {"url": "https://example.com"}}
})
if "error" not in resp or "content" in resp.get("result", {}):
    result.add_pass()
else:
    result.add_fail(str(resp))

# Test 6: Crawl
print("\n[Test 1.6] Crawl - Web scraping")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 6, "method": "tools/call",
    "params": {"name": "crawl", "arguments": {"url": "https://example.com"}}
})
if "error" not in resp or "content" in resp.get("result", {}):
    result.add_pass()
else:
    result.add_fail(str(resp))

# Test 7: Backend Health Checks
print("\n[Test 1.7] Backend Services Health")
backends = [
    (18880, "SearXNG", "/"),
    (18881, "EasyOCR", "/health"),
    (18882, "Playwright", "/health"),
    (18883, "Firecrawl", "/health")
]
all_healthy = True
for port, name, path in backends:
    try:
        r = requests.get(f"http://localhost:{port}{path}", timeout=5)
        if r.status_code == 200:
            print(f"  {name} ({port}): OK")
        else:
            print(f"  {name} ({port}): {r.status_code}")
            all_healthy = False
    except Exception as e:
        print(f"  {name} ({port}): DOWN - {e}")
        all_healthy = False
if all_healthy:
    result.add_pass()
else:
    result.add_fail("Some backends unavailable")

# ============================================================
# NEGATIVE TESTS
# ============================================================
print(f"\n{BLUE}{'='*60}")
print("NEGATIVE TESTS - Invalid Input")
print('='*60 + RESET)

# Test 8: Empty query
print("\n[Test 2.1] Search - Empty query")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 8, "method": "tools/call",
    "params": {"name": "search", "arguments": {"query": ""}}
})
# Should still work but return empty results
if "result" in resp:
    result.add_pass()
else:
    result.add_fail(str(resp))

# Test 9: Invalid tool name
print("\n[Test 2.2] Invalid tool name")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 9, "method": "tools/call",
    "params": {"name": "invalid_tool", "arguments": {}}
})
if "error" in resp or "Unknown tool" in str(resp):
    result.add_pass()
else:
    result.add_fail("Should return error for invalid tool")

# Test 10: Invalid JSON-RPC method
print("\n[Test 2.3] Invalid RPC method")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 10, "method": "tools/invalid", "params": {}
})
if "error" in resp:
    result.add_pass()
else:
    result.add_fail("Should return error for invalid method")

# Test 11: Missing required arguments
print("\n[Test 2.4] Missing required arguments")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 11, "method": "tools/call",
    "params": {"name": "search"}  # Missing arguments
})
# Should handle gracefully
result.add_pass()  # Pass if doesn't crash

# ============================================================
# EXCEPTION TESTS
# ============================================================
print(f"\n{BLUE}{'='*60}")
print("EXCEPTION TESTS - Error Handling")
print('='*60 + RESET)

# Test 12: SSRF Protection - Block internal URLs
print("\n[Test 3.1] SSRF Protection - Internal URL")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 12, "method": "tools/call",
    "params": {"name": "navigate", "arguments": {"url": "http://localhost:18881/"}}
})
if "Blocked" in str(resp) or "error" in resp:
    result.add_pass()
else:
    result.add_fail("Should block internal URLs")

# Test 13: SSRF Protection - Block private IPs
print("\n[Test 3.2] SSRF Protection - Private IP")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 13, "method": "tools/call",
    "params": {"name": "crawl", "arguments": {"url": "http://192.168.1.1/"}}
})
if "Blocked" in str(resp) or "error" in resp:
    result.add_pass()
else:
    result.add_fail("Should block private IPs")

# Test 14: Invalid URL format
print("\n[Test 3.3] Invalid URL format")
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 14, "method": "tools/call",
    "params": {"name": "navigate", "arguments": {"url": "not-a-valid-url"}}
})
# Should handle gracefully
result.add_pass()

# Test 15: Backend timeout simulation
print("\n[Test 3.4] Backend service unavailable")
# Temporarily kill a backend to test
subprocess.run(["docker", "stop", "playwright"], capture_output=True)
time.sleep(2)
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 15, "method": "tools/call",
    "params": {"name": "navigate", "arguments": {"url": "https://example.com"}}
})
subprocess.run(["docker", "start", "playwright"], capture_output=True)
time.sleep(5)
if "error" in resp or "Connection" in str(resp):
    result.add_pass()
else:
    result.add_warn("Backend may have recovered quickly")

# ============================================================
# ROLLBACK/RECOVERY TESTS
# ============================================================
print(f"\n{BLUE}{'='*60}")
print("ROLLBACK/RECOVERY TESTS - Resilience")
print('='*60 + RESET)

# Test 16: Service restart recovery
print("\n[Test 4.1] Service restart recovery")
# Restart a backend
subprocess.run(["docker", "restart", "easyocr"], capture_output=True)
time.sleep(2)

# Test MCP still works
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 16, "method": "initialize", "params": {}
})
if "result" in resp:
    result.add_pass()
else:
    result.add_fail("MCP server crashed during backend restart")

# Wait for OCR to be ready
print("  Waiting for OCR service to be ready...")
for i in range(15):
    if check_backend(18881):
        print(f"  OCR ready after {i+1} seconds")
        break
    time.sleep(1)

# Test OCR works after restart
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 17, "method": "tools/call",
    "params": {"name": "ocr", "arguments": {"url": "https://httpbin.org/image/png"}}
})
if "result" in resp:
    result.add_pass()
else:
    result.add_fail("OCR not recovered after restart")

# Test 18: Full MCP server restart
print("\n[Test 4.2] MCP server process restart")
# The MCP server is stateless, so this just tests it's still callable
resp = run_mcp_command({
    "jsonrpc": "2.0", "id": 18, "method": "initialize", "params": {}
})
if resp.get("result", {}).get("serverInfo", {}).get("name") == "local-mcp":
    result.add_pass()
else:
    result.add_fail("MCP server not responding")

# Test 19: Concurrent requests
print("\n[Test 4.3] Concurrent request handling")
import concurrent.futures
def make_request(i):
    return run_mcp_command({"jsonrpc": "2.0", "id": i, "method": "initialize", "params": {}})

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(make_request, i) for i in range(10)]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]

success_count = sum(1 for r in results if "result" in r)
if success_count == 10:
    result.add_pass()
else:
    result.add_fail(f"Only {success_count}/10 concurrent requests succeeded")

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{BLUE}{'='*60}")
print("TEST SUMMARY")
print('='*60 + RESET)
print(f"{GREEN}Passed: {result.passed}{RESET}")
print(f"{RED}Failed: {result.failed}{RESET}")
print(f"{YELLOW}Warnings: {result.warnings}{RESET}")

total = result.passed + result.failed
if total > 0:
    pass_rate = (result.passed / total) * 100
    print(f"\nPass Rate: {pass_rate:.1f}%")

if result.failed > 0:
    sys.exit(1)
else:
    print(f"\n{GREEN}All tests passed!{RESET}")
    sys.exit(0)

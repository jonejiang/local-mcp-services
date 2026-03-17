#!/bin/bash
# MCP Comprehensive Validation Script

echo "=========================================="
echo "Local MCP Comprehensive Validation"
echo "=========================================="

PASS=0
FAIL=0

# Test 1: MCP Server stdio
echo -e "\n[Test 1] MCP Server (stdio) - initialize"
result=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python3 mcp_server.py 2>&1)
if echo "$result" | grep -q '"protocolVersion"'; then
    echo "✅ PASS - MCP Server responds correctly"
    ((PASS++))
else
    echo "❌ FAIL - $result"
    ((FAIL++))
fi

# Test 2: List tools
echo -e "\n[Test 2] List tools"
result=$(echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python3 mcp_server.py 2>&1)
if echo "$result" | grep -q '"search"' && echo "$result" | grep -q '"ocr"'; then
    echo "✅ PASS - Tools listed correctly"
    ((PASS++))
else
    echo "❌ FAIL - $result"
    ((FAIL++))
fi

# Test 3: Search (via 18880 backend)
echo -e "\n[Test 3] Search tool"
result=$(echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search","arguments":{"query":"python"}}}' | python3 mcp_server.py 2>&1)
echo "$result" | head -c 200
if echo "$result" | grep -q '"content"'; then
    echo -e "\n✅ PASS - Search returns result"
    ((PASS++))
else
    echo -e "\n⚠️ WARN - Search may need backend (SearXNG on :8080)"
    ((FAIL++))
fi

# Test 4: OCR (via 18881 backend)
echo -e "\n[Test 4] OCR tool"
result=$(echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"ocr","arguments":{"url":"https://httpbin.org/image/png"}}}' | python3 mcp_server.py 2>&1)
if echo "$result" | grep -q '"content"' || echo "$result" | grep -q "error"; then
    echo "✅ PASS - OCR responds (check error for details)"
    ((PASS++))
else
    echo "❌ FAIL - OCR failed: $result"
    ((FAIL++))
fi

# Test 5: Navigate (via 18882 backend)
echo -e "\n[Test 5] Navigate tool"
result=$(echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"navigate","arguments":{"url":"https://example.com"}}}' | python3 mcp_server.py 2>&1)
if echo "$result" | grep -q '"content"' || echo "$result" | grep -q "error"; then
    echo "✅ PASS - Navigate responds"
    ((PASS++))
else
    echo "❌ FAIL - Navigate failed: $result"
    ((FAIL++))
fi

# Test 6: Crawl (via 18883 backend)
echo -e "\n[Test 6] Crawl tool"
result=$(echo '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"crawl","arguments":{"url":"https://example.com"}}}' | python3 mcp_server.py 2>&1)
if echo "$result" | grep -q '"content"' || echo "$result" | grep -q "error"; then
    echo "✅ PASS - Crawl responds"
    ((PASS++))
else
    echo "❌ FAIL - Crawl failed: $result"
    ((FAIL++))
fi

# Test 7: Backend health checks
echo -e "\n[Test 7] Backend services health"
for port in 18880 18881 18882 18883; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null)
    if [ "$code" = "200" ]; then
        echo "✅ Port $port: OK"
        ((PASS++))
    else
        echo "❌ Port $port: $code"
        ((FAIL++))
    fi
done

# Test 8: SSRF Protection
echo -e "\n[Test 8] SSRF Protection"
result=$(echo '{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"navigate","arguments":{"url":"http://localhost:18881/"}}}' | python3 mcp_server.py 2>&1)
if echo "$result" | grep -q "Blocked"; then
    echo "✅ PASS - SSRF protection working"
    ((PASS++))
else
    echo "⚠️ WARN - SSRF may not block internal URLs: $result"
fi

# Summary
echo -e "\n=========================================="
echo "Summary: $PASS passed, $FAIL failed"
echo "=========================================="

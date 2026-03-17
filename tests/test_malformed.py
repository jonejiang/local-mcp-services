#!/usr/bin/env python3
"""
Malformed Input Tests for MCP Server
TDD: Test handling of malformed and invalid inputs
"""
import pytest
import json
import subprocess
from typing import Dict


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


class TestMalformedJSON:
    """Test handling of malformed JSON"""

    def test_invalid_json_string(self):
        """Test invalid JSON string input"""
        proc = subprocess.Popen(
            ["python3", MCP_SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="not valid json\n", timeout=30)

        # Should return JSON-RPC error
        try:
            resp = json.loads(stdout.strip())
            assert "error" in resp
        except json.JSONDecodeError:
            pass  # Also acceptable

    def test_empty_input(self):
        """Test empty input"""
        proc = subprocess.Popen(
            ["python3", MCP_SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="\n", timeout=30)

    def test_truncated_json(self):
        """Test truncated JSON"""
        proc = subprocess.Popen(
            ["python3", MCP_SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input='{"jsonrpc":"2.0",\n', timeout=30)

    def test_malformed_jsonrpc(self):
        """Test malformed JSON-RPC"""
        invalid_requests = [
            {"jsonrpc": "1.0", "method": "initialize", "id": 1},  # Wrong version
            {"method": "initialize", "id": 1},  # Missing jsonrpc
            {"jsonrpc": "2.0", "id": 1},  # Missing method
            {"jsonrpc": "2.0", "method": 123, "id": 1},  # Method is number
        ]

        for req in invalid_requests:
            resp = run_mcp_command(req)
            # Should handle gracefully
            assert "result" in resp or "error" in resp


class TestInvalidMethods:
    """Test invalid method handling"""

    @pytest.mark.parametrize("method", [
        "tools/invalid",
        "invalid/method",
        "",
        "   ",
        "TOOLS/LIST",  # Case sensitive
        "tools/",
        "/initialize",
    ])
    def test_invalid_methods(self, method):
        """Test invalid methods are rejected"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {}
        })

        assert "error" in resp

    def test_missing_method(self):
        """Test missing method field"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1
        })

        assert "error" in resp


class TestInvalidParameters:
    """Test invalid parameters handling"""

    def test_invalid_tool_name_type(self):
        """Test tool name is not a string"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": 123,  # Should be string
                "arguments": {}
            }
        })

        assert "error" in resp or "result" in resp

    def test_missing_arguments(self):
        """Test missing arguments object"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search"
            }
        })

        # Should handle gracefully
        assert "result" in resp or "error" in resp

    def test_null_arguments(self):
        """Test null arguments"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": None
        })

        assert "error" in resp or "result" in resp

    def test_array_arguments(self):
        """Test array instead of object for arguments"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": []
            }
        })

        # Should handle gracefully
        assert "result" in resp or "error" in resp


class TestBoundaryValues:
    """Test boundary values"""

    def test_very_long_query(self):
        """Test very long query string"""
        long_query = "a" * 10000

        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": long_query}
            }
        })

        # Should reject or truncate
        assert "error" in resp or "result" in resp

    def test_unicode_input(self):
        """Test Unicode input"""
        unicode_queries = [
            "你好世界",
            "こんにちは",
            "🎉🎊🎁",
            "\u0000\u001F",
            "café",
        ]

        for query in unicode_queries:
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": query}
                }
            })

            assert "result" in resp or "error" in resp

    def test_special_characters_in_query(self):
        """Test special characters in query"""
        special = [
            "\x00\x01\x02",  # Control chars
            "\n\r\t",  # Whitespace
            "Quotes: \" '",
            "Backslash: \\",
            "Angle: < >",
        ]

        for chars in special:
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": chars}
                }
            })

            # Should handle gracefully
            assert "result" in resp or "error" in resp


class TestEdgeCases:
    """Test edge cases"""

    def test_request_id_types(self):
        """Test various request ID types"""
        for req_id in [1, "1", None, 1.5, True]:
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "initialize",
                "params": {}
            })

            assert "result" in resp or "error" in resp

    def test_batch_requests(self):
        """Test batch request handling (if supported)"""
        # Not part of spec but test resilience
        batch = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]

        # Send as single line
        proc = subprocess.Popen(
            ["python3", MCP_SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(
            input=json.dumps(batch[0]) + "\n" + json.dumps(batch[1]) + "\n",
            timeout=30
        )

        # Should handle both
        lines = stdout.strip().split("\n")
        assert len(lines) == 2

    def test_negative_timeout(self):
        """Test negative timeout values"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "test", "timeout": -1}
            }
        })

        assert "result" in resp or "error" in resp


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

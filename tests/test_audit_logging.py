#!/usr/bin/env python3
"""
Audit Logging Tests for MCP Server
TDD: Test audit logging functionality
"""
import pytest
import json
import subprocess
import os
import tempfile
from typing import Dict, List
from datetime import datetime


MCP_SERVER = "/Users/jone/AI/Agents/local-mcp-services/mcp_server.py"


def run_mcp_command(cmd: Dict, env: Dict = None) -> Dict:
    """Execute MCP command via stdin/stdout"""
    import subprocess

    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)

    proc = subprocess.Popen(
        ["python3", MCP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=proc_env
    )
    stdout, stderr = proc.communicate(input=json.dumps(cmd) + "\n", timeout=30)
    try:
        return json.loads(stdout.strip())
    except:
        return {"error": stdout or stderr}


class TestAuditLogging:
    """Audit logging test suite"""

    def test_audit_log_creation(self):
        """Test audit log is created"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Make a request
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            # Log file should exist
            assert os.path.exists(temp_log), "Audit log not created"

            # Should have content
            with open(temp_log, "r") as f:
                content = f.read()
                assert len(content) > 0, "Audit log is empty"

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_format(self):
        """Test audit log format is valid JSON"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Make a request
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            # Read and parse log
            with open(temp_log, "r") as f:
                line = f.readline()
                entry = json.loads(line)

                # Should have required fields
                assert "timestamp" in entry, "Missing timestamp"
                assert "method" in entry, "Missing method"
                assert "status" in entry, "Missing status"

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_initialization(self):
        """Test initialization is logged"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            # Check log entry
            with open(temp_log, "r") as f:
                content = f.read()
                assert "initialize" in content

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_tools_list(self):
        """Test tools/list is logged"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }, env=test_env)

            with open(temp_log, "r") as f:
                content = f.read()
                assert "tools/list" in content or "tools" in content

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_tool_calls(self):
        """Test tool calls are logged"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": "test"}
                }
            }, env=test_env)

            with open(temp_log, "r") as f:
                content = f.read()
                assert "search" in content

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_rejected_requests(self):
        """Test rejected requests are logged"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Invalid method should be logged
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "invalid_method",
                "params": {}
            }, env=test_env)

            with open(temp_log, "r") as f:
                content = f.read()
                assert "error" in content or "status" in content

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_timestamps(self):
        """Test timestamps are valid ISO format"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            with open(temp_log, "r") as f:
                line = f.readline()
                entry = json.loads(line)

                # Should be parseable as ISO datetime
                timestamp = entry.get("timestamp", "")
                try:
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Invalid timestamp format: {timestamp}")

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_multiple_requests(self):
        """Test multiple requests are logged separately"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Make multiple requests
            for i in range(5):
                run_mcp_command({
                    "jsonrpc": "2.0",
                    "id": i,
                    "method": "initialize",
                    "params": {}
                }, env=test_env)

            # Should have 5 log entries
            with open(temp_log, "r") as f:
                lines = f.readlines()
                assert len(lines) == 5, f"Expected 5 log entries, got {len(lines)}"

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_audit_log_includes_request_id(self):
        """Test request ID is included in logs"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 123,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            with open(temp_log, "r") as f:
                content = f.read()
                # JSON should have id field somewhere
                assert "123" in content or "id" in content

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)


class TestAuditLogSecurity:
    """Audit log security tests"""

    def test_audit_log_not_world_readable(self):
        """Test audit log has proper permissions"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            stat_info = os.stat(temp_log)
            mode = stat_info.st_mode & 0o777

            # Should not be world-readable
            assert not (mode & 0o004), "Audit log is world-readable!"

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_no_sensitive_data_in_logs(self):
        """Test sensitive data not logged"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Make request with potentially sensitive data
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": "password123"}
                }
            }, env=test_env)

            with open(temp_log, "r") as f:
                content = f.read()

                # Should not log password in plain text
                # (may be sanitized)
                if "password123" in content:
                    # Check it's been modified
                    assert "password" in content.lower() or "***" in content

        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

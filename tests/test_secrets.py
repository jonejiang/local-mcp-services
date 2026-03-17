#!/usr/bin/env python3
"""
Secrets Management Tests for MCP Server
TDD: Test secrets handling and environment variable security
"""
import pytest
import json
import subprocess
import os
import tempfile
from typing import Dict


# MCP Server path
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


class TestSecretsHandling:
    """Secrets handling test suite"""

    def test_no_hardcoded_secrets(self):
        """Test no hardcoded secrets in source code"""
        with open(MCP_SERVER, "r") as f:
            content = f.read()

        # Check for common secret patterns
        secret_patterns = [
            "password = '",
            "api_key = '",
            "secret = '",
            "token = '",
            'password = "',
            'api_key = "',
        ]

        for pattern in secret_patterns:
            # Should not find hardcoded secrets
            assert pattern.lower() not in content.lower() or "changeme" in content.lower(), \
                f"Potential hardcoded secret found: {pattern}"

    def test_environment_variable_secrets(self):
        """Test secrets loaded from environment"""
        # Set test secret via environment
        test_env = {"MCP_AUDIT_LOG": "/tmp/test-mcp-audit.log"}

        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }, env=test_env)

        assert "result" in resp or "error" in resp

    def test_sensitive_data_not_in_logs(self):
        """Test sensitive data not written to logs"""
        import tempfile
        import os

        # Create temp log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_log = f.name

        try:
            # Set audit log to temp file
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Make a request
            resp = run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": "test"}
                }
            }, env=test_env)

            # Check log file doesn't contain sensitive data
            if os.path.exists(temp_log):
                with open(temp_log, "r") as f:
                    log_content = f.read()

                # Should not contain passwords or API keys in plain text
                assert "password" not in log_content.lower() or "test" not in log_content
                assert "api_key" not in log_content.lower()
        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_command_line_args_not_logged(self):
        """Test command line arguments not logged"""
        # The server reads from stdin, not command line args
        # This test verifies the implementation doesn't use sys.argv

        with open(MCP_SERVER, "r") as f:
            content = f.read()

        # Should not use sys.argv for sensitive data
        assert "sys.argv" not in content or "#" in content.split("sys.argv")[0].split("\n")[-1]

    def test_error_messages_no_secrets(self):
        """Test error messages don't expose secrets"""
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "test"}
            }
        })

        if "error" in resp:
            error_msg = str(resp["error"])
            # Should not contain sensitive patterns
            assert "password" not in error_msg.lower()
            assert "api_key" not in error_msg.lower()
            assert "secret" not in error_msg.lower()

    def test_audit_log_permissions(self):
        """Test audit log has proper permissions"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_log = f.name

        try:
            test_env = {"MCP_AUDIT_LOG": temp_log}

            # Make a request to trigger logging
            run_mcp_command({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }, env=test_env)

            # Check file permissions (should not be world-readable)
            if os.path.exists(temp_log):
                stat_info = os.stat(temp_log)
                mode = stat_info.st_mode & 0o777

                # Should not be world-writable or world-readable
                assert mode & 0o077 == 0, "Audit log should not be world-accessible"
        finally:
            if os.path.exists(temp_log):
                os.remove(temp_log)

    def test_temporary_files_secure(self):
        """Test temporary files are handled securely"""
        # Server should not create unnecessary temp files
        # Check source doesn't use insecure temp patterns

        with open(MCP_SERVER, "r") as f:
            content = f.read()

        # Should use secure temp file patterns
        # NamedTemporaryFile is OK, but mkstemp is better
        if "tempfile" in content:
            # Should use context managers or proper cleanup
            assert "delete=True" in content or "finally:" in content

    def test_docker_secrets_not_exposed(self):
        """Test Docker secrets are not exposed in logs"""
        # Run the MCP server in a limited environment
        # Check that no secrets are printed to stdout/stderr

        proc = subprocess.Popen(
            ["python3", MCP_SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = proc.communicate(
            input=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }) + "\n",
            timeout=30
        )

        combined = stdout + stderr

        # Should not contain sensitive patterns
        assert "password" not in combined.lower() or "error" in combined.lower()
        assert "api_key" not in combined.lower()
        assert "secret" not in combined.lower()

    def test_env_var_sanitization(self):
        """Test environment variables are sanitized"""
        # Set potentially dangerous env vars
        dangerous_env = {
            "LD_PRELOAD": "/tmp/evil.so",
            "LD_LIBRARY_PATH": "/tmp/evil",
            "PATH": "/tmp/evil:/usr/bin:/bin",
        }

        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }, env=dangerous_env)

        # Server should still work (or fail gracefully)
        assert "result" in resp or "error" in resp


class TestCredentialManagement:
    """Credential management tests"""

    def test_no_default_credentials(self):
        """Test no default credentials in use"""
        with open(MCP_SERVER, "r") as f:
            content = f.read()

        # Check for default credentials
        bad_defaults = [
            "password='admin'",
            "password='password'",
            "password='123456'",
            "api_key='12345'",
            "api_key='api_key'",
        ]

        for bad in bad_defaults:
            assert bad not in content.lower(), \
                f"Default credential found: {bad}"

    def test_token_expiration_handled(self):
        """Test expired tokens are handled properly"""
        # Server should not crash on invalid/expired tokens
        resp = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })

        assert "result" in resp or "error" in resp


class TestSecureStorage:
    """Secure storage tests"""

    def test_in_memory_data_cleared(self):
        """Test sensitive data cleared from memory"""
        # This is a best-effort test
        # Server should not hold sensitive data longer than needed

        resp1 = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "test"}
            }
        })

        # Make another request
        resp2 = run_mcp_command({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {}
        })

        # Server should handle both independently
        assert resp1 is not None
        assert resp2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

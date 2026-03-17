#!/usr/bin/env python3
"""
Local MCP Server - Security Enhanced v7.0
Comprehensive Security Features for Production

Security Features:
- Thread-safe rate limiting (per-tool)
- SSRF protection with DNS rebinding prevention
- SQL/Command/XSS injection detection
- Input sanitization
- Audit logging
- Tool whitelist
- Request size limits
- Timeout handling
"""

import json
import sys
import re
import time
import os
import logging
import threading
import hashlib
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# ========== Configuration ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.environ.get("MCP_AUDIT_LOG", "/tmp/mcp-audit.log")

# ========== Logging Configuration ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger("mcp-server")

# ========== Security Constants ==========
SSRF_BLOCKED_RANGES = [
    # Loopback
    "127.", "::1", "localhost",
    # Private IPv4
    "10.",                           # 10.0.0.0/8
    "172.16.", "172.17.", "172.18.",  # 172.16.0.0/12
    "172.19.", "172.2",
    "192.168.",                      # 192.168.0.0/16
    # Link-local (cloud metadata)
    "169.254.",                      # AWS/GCP/Azure metadata
    # Special
    "0.", "100.",
    # IPv6
    "fc00::/", "fe80::/",
]

# SQL Injection detection patterns
SQL_INJECTION_PATTERNS = [
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b",
    r"(--|;|'|\"|%27|%22)",
    r"\bOR\b.*=.*\b",
    r"EXEC(\(|UTE|XPCMD|sp_executesql)",
    r"0x[0-9a-fA-F]+",  # Hex values
    r"WAITFOR\s+DELAY",
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"[;&|`$]", r"\|\|", r"&&", r"\$\(", r"`",
    r"\|\s*rm", r"\|\s*cat", r"\|\s*wget", r"\|\s*curl",
]

# XSS detection patterns
XSS_PATTERNS = [
    r"<script", r"javascript:", r"onerror=", r"onload=",
    r"onclick=", r"onmouseover=", r"onfocus=",
    r"<iframe", r"<embed", r"<object",
]

# Tool whitelist with specifications
ALLOWED_TOOLS = {
    "search": {
        "description": "Web search using SearXNG",
        "required_params": ["query"],
        "optional_params": ["format", "language"],
        "max_query_length": 1000,
        "rate_limit": 30,  # per minute
        "timeout": 10,
    },
    "ocr": {
        "description": "OCR image to text using EasyOCR",
        "required_params": ["url"],
        "allowed_schemes": ["https"],
        "rate_limit": 10,  # per minute
        "timeout": 60,
    },
    "navigate": {
        "description": "Navigate to URL using Playwright",
        "required_params": ["url"],
        "allowed_schemes": ["https"],
        "rate_limit": 20,  # per minute
        "timeout": 30,
    },
    "crawl": {
        "description": "Crawl webpage using Firecrawl",
        "required_params": ["url"],
        "allowed_schemes": ["https"],
        "rate_limit": 10,  # per minute
        "timeout": 60,
    },
}

# Maximum request size (1MB)
MAX_REQUEST_SIZE = 1024 * 1024

# ========== Data Classes ==========
@dataclass
class RequestLog:
    """Request log entry"""
    timestamp: str
    method: str
    tool: str
    ip: str
    user_agent: str
    status: str
    error: Optional[str] = None

@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_ssrf_protection: bool = True
    enable_rate_limiting: bool = True
    enable_input_validation: bool = True
    enable_audit_logging: bool = True
    max_request_size: int = MAX_REQUEST_SIZE

# ========== Thread-Safe Components ==========
class ThreadSafeRateLimiter:
    """Thread-safe rate limiter with sliding window"""
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request is allowed under rate limit"""
        with self._lock:
            now = time.time()
            # Clean up old requests
            if key in self.requests:
                self.requests[key] = [t for t in self.requests[key] if now - t < window]
            else:
                self.requests[key] = []

            if len(self.requests[key]) >= limit:
                return False

            self.requests[key].append(now)
            return True

    def get_remaining(self, key: str, limit: int, window: int = 60) -> int:
        """Get remaining requests allowed"""
        with self._lock:
            now = time.time()
            if key in self.requests:
                active = [t for t in self.requests[key] if now - t < window]
                return max(0, limit - len(active))
            return limit

# Global rate limiter instance
rate_limiter = ThreadSafeRateLimiter()

# ========== Audit Logger ==========
class AuditLogger:
    """Thread-safe audit logger"""
    def __init__(self, log_file: str = LOG_FILE):
        self.log_file = log_file
        self._lock = threading.Lock()

    def log_request(self, log_entry: RequestLog):
        """Log request to audit file"""
        with self._lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(log_entry.__dict__, default=str) + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent audit logs"""
        logs = []
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line.strip()))
                    except:
                        pass
        except:
            pass
        return logs

# Global audit logger instance
audit_logger = AuditLogger()

# ========== Security Functions ==========

def validate_url(url: str) -> Optional[str]:
    """
    Validate URL - SSRF protection
    Returns error message if blocked, None if valid
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # Check empty host
        if not host:
            return "Empty hostname"

        # Hostname blacklist check
        for blocked in SSRF_BLOCKED_RANGES:
            if host.startswith(blocked) or host == blocked.rstrip('.'):
                return f"Blocked hostname: {host}"

        # DNS rebinding protection - resolve and check IP
        try:
            import socket
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror:
                # DNS resolution failed, but hostname format is valid
                return None

            for blocked in SSRF_BLOCKED_RANGES:
                if ip.startswith(blocked):
                    return f"Blocked resolved IP: {ip} (for host: {host})"
        except Exception as e:
            logger.warning(f"DNS resolution failed for {host}: {e}")

        # Protocol whitelist
        if parsed.scheme not in ["http", "https"]:
            return f"Unsupported scheme: {parsed.scheme}"

        return None
    except Exception as e:
        return f"URL parsing error: {e}"


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input
    - Length limit
    - Remove null bytes
    - Remove non-printable characters
    """
    if not text:
        return ""

    # Length limit
    text = text[:max_length]

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove non-printable characters (keep whitespace)
    text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')

    return text


def detect_injection(text: str, patterns: List[str]) -> Optional[str]:
    """
    Detect injection attempts
    Returns detected pattern if found, None otherwise
    """
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return f"Pattern detected: {pattern[:50]}"
    return None


def validate_tool_input(tool_name: str, arguments: Dict) -> Optional[str]:
    """
    Comprehensive input validation for tool calls
    Returns error message if validation fails, None if valid
    """
    logger.info(f"Validating tool: {tool_name}")

    # 1. Tool whitelist check
    if tool_name not in ALLOWED_TOOLS:
        return f"Unknown tool: {tool_name}"

    tool_spec = ALLOWED_TOOLS[tool_name]

    # 2. Rate limiting
    if tool_spec.get("rate_limit"):
        rate_limit = tool_spec["rate_limit"]
        if not rate_limiter.is_allowed(tool_name, rate_limit):
            remaining = rate_limiter.get_remaining(tool_name, rate_limit)
            logger.warning(f"Rate limit exceeded for {tool_name}. Remaining: {remaining}")
            return f"Rate limit exceeded for {tool_name}. Try again later."

    # 3. Required parameters check
    for param in tool_spec.get("required_params", []):
        if param not in arguments:
            return f"Missing required parameter: {param}"

    # 4. URL parameter validation
    if "url" in arguments:
        url = arguments["url"]

        # SSRF protection
        error = validate_url(url)
        if error:
            logger.warning(f"SSRF blocked: {url} - {error}")
            return f"URL blocked: {error}"

        # Protocol whitelist
        parsed = urlparse(url)
        allowed = tool_spec.get("allowed_schemes", ["https"])
        if parsed.scheme not in allowed:
            return f"Scheme {parsed.scheme} not allowed. Use: {', '.join(allowed)}"

    # 5. Query parameter validation
    if "query" in arguments:
        query = arguments["query"]

        # Length check
        max_len = tool_spec.get("max_query_length", 1000)
        if len(query) > max_len:
            return f"Query too long (max {max_len} characters)"

        # SQL injection detection
        error = detect_injection(query, SQL_INJECTION_PATTERNS)
        if error:
            logger.warning(f"SQL injection detected: {query[:50]}...")
            return f"Input validation failed: potential SQL injection detected"

        # Command injection detection
        error = detect_injection(query, COMMAND_INJECTION_PATTERNS)
        if error:
            logger.warning(f"Command injection detected: {query[:50]}...")
            return f"Input validation failed: potential command injection detected"

        # XSS detection
        error = detect_injection(query, XSS_PATTERNS)
        if error:
            logger.warning(f"XSS detected: {query[:50]}...")
            return f"Input validation failed: potential XSS detected"

    # 6. Sanitize all string inputs
    for key, value in arguments.items():
        if isinstance(value, str):
            max_len = tool_spec.get("max_query_length", 1000) if key == "query" else 10000
            arguments[key] = sanitize_input(value, max_len)

    logger.info(f"Validation passed for {tool_name}")
    return None


def get_backend_url(tool_name: str) -> str:
    """Get backend service URL for tool"""
    # Check if running in sandbox mode
    sandbox_mode = os.environ.get("MCP_SANDBOX", "false").lower() == "true"
    base_port = 28880 if sandbox_mode else 18880

    backend_map = {
        "search": f"http://localhost:{base_port}",
        "ocr": f"http://localhost:{base_port + 1}",
        "navigate": f"http://localhost:{base_port + 2}",
        "crawl": f"http://localhost:{base_port + 3}",
    }
    return backend_map.get(tool_name, "")


def handle_request(req: Dict) -> Dict:
    """
    Handle MCP request with full security checks
    """
    method = req.get("method")
    params = req.get("params", {})
    msg_id = req.get("id")

    # Log incoming request
    client_ip = req.get("ip", "unknown")
    user_agent = req.get("user_agent", "unknown")

    logger.info(f"Request: {method}")

    # Audit log entry
    log_entry = RequestLog(
        timestamp=datetime.now().isoformat(),
        method=method,
        tool=params.get("name", ""),
        ip=client_ip,
        user_agent=user_agent,
        status="started"
    )

    # Handle tools/call
    if method == "tools/call":
        tool = params.get("name", "")
        args = params.get("arguments", {})

        # Input validation
        error = validate_tool_input(tool, args)
        if error:
            logger.warning(f"Validation failed: {error}")
            log_entry.status = "rejected"
            log_entry.error = error
            audit_logger.log_request(log_entry)

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": error}
            }

        # Call backend service
        try:
            backend_url = get_backend_url(tool)
            import requests as req_lib

            if tool == "search":
                # SearXNG uses /search endpoint with q parameter
                response = req_lib.get(
                    f"{backend_url}/search",
                    params={"q": args.get("query", ""), "format": "json"},
                    timeout=ALLOWED_TOOLS["search"]["timeout"]
                )
                results = response.json().get("results", [])[:5] if response.status_code == 200 else []
                text = "\n".join([f"- {r.get('title','')}: {r.get('url','')}" for r in results])

            elif tool == "ocr":
                response = req_lib.post(
                    f"{backend_url}/ocr",
                    json={"url": args.get("url", "")},
                    timeout=ALLOWED_TOOLS["ocr"]["timeout"]
                )
                text = response.json().get("text", "") if response.status_code == 200 else response.text

            elif tool == "navigate":
                response = req_lib.post(
                    f"{backend_url}/navigate",
                    json={"url": args.get("url", "")},
                    timeout=ALLOWED_TOOLS["navigate"]["timeout"]
                )
                data = response.json() if response.status_code == 200 else {}
                text = f"Title: {data.get('title','')}\nURL: {data.get('url','')}"

            elif tool == "crawl":
                response = req_lib.post(
                    f"{backend_url}/crawl",
                    json={"url": args.get("url", "")},
                    timeout=ALLOWED_TOOLS["crawl"]["timeout"]
                )
                data = response.json() if response.status_code == 200 else {}
                text = data.get("content", "")[:1000] if data else ""

            else:
                text = f"Unknown tool: {tool}"

            log_entry.status = "success"
            audit_logger.log_request(log_entry)

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}]}
            }

        except Exception as e:
            logger.error(f"Backend error: {e}")
            log_entry.status = "error"
            log_entry.error = str(e)
            audit_logger.log_request(log_entry)

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": str(e)}
            }

    # Handle initialize
    if method == "initialize":
        log_entry.status = "success"
        audit_logger.log_request(log_entry)

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "local-mcp", "version": "7.0.0"},
                "capabilities": {"tools": {}}
            }
        }

    # Handle tools/list
    if method == "tools/list":
        log_entry.status = "success"
        audit_logger.log_request(log_entry)

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": name,
                        "description": spec["description"],
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                p: {"type": "string"}
                                for p in spec.get("required_params", []) + spec.get("optional_params", [])
                            },
                            "required": spec.get("required_params", [])
                        }
                    }
                    for name, spec in ALLOWED_TOOLS.items()
                ]
            }
        }

    # Unknown method
    log_entry.status = "error"
    log_entry.error = f"Unknown method: {method}"
    audit_logger.log_request(log_entry)

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"}
    }


def main():
    """Main loop - read JSON-RPC from stdin"""
    logger.info("MCP Server starting...")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            # Check request size
            if len(line) > MAX_REQUEST_SIZE:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Request too large"}
                }), flush=True)
                continue

            req = json.loads(line.strip())
            resp = handle_request(req)
            print(json.dumps(resp), flush=True)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"}
            }), flush=True)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            }), flush=True)


if __name__ == "__main__":
    main()

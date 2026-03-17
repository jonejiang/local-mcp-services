"""
Shared MCP Service Settings
Configuration for all local MCP services
"""

# Service Ports
PORTS = {
    "searxng": 18880,
    "easyocr": 18881,
    "playwright": 18882,
    "firecrawl": 18883,
}

# Security Settings
SECURITY = {
    # SSRF Protection: Blocked IP ranges
    "blocked_ip_ranges": [
        "127.",
        "10.",
        "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.",
        "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.",
        "192.168.",
        "169.254.",
    ],
    # Blocked domains
    "blocked_domains": [
        "localhost",
        "metadata.google.internal",
        "metadata.azure.com",
        "169.254.169.254",
    ],
    # Request timeouts (seconds)
    "request_timeout": 30,
    # Max request size (bytes)
    "max_request_size": 10 * 1024 * 1024,  # 10MB
}

# Resource Limits
RESOURCE_LIMITS = {
    "searxng": {
        "memory": "512m",
        "cpus": 0.5,
    },
    "easyocr": {
        "memory": "4g",
        "cpus": 2.0,
    },
    "playwright": {
        "memory": "2g",
        "cpus": 1.0,
    },
    "firecrawl": {
        "memory": "1g",
        "cpus": 0.5,
    },
}

# Health Check Settings
HEALTH_CHECK = {
    "interval": "30s",
    "timeout": "10s",
    "retries": 3,
}

# MCP Server Configuration Templates
MCP_CONFIGS = {
    "claude_code": {
        "local-search": {
            "url": "http://localhost:18880/mcp"
        },
        "local-ocr": {
            "url": "http://localhost:18881/mcp"
        },
        "local-playwright": {
            "url": "http://localhost:18882/mcp"
        },
        "local-firecrawl": {
            "url": "http://localhost:18883/mcp"
        }
    },
    "openclaw": {
        "local-search": {
            "url": "http://host.docker.internal:18880/mcp"
        },
        "local-ocr": {
            "url": "http://host.docker.internal:18881/mcp"
        },
        "local-playwright": {
            "url": "http://host.docker.internal:18882/mcp"
        },
        "local-firecrawl": {
            "url": "http://host.docker.internal:18883/mcp"
        }
    }
}

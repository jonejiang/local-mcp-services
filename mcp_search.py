#!/usr/bin/env python3
"""
MCP Server for SearXNG Search
Implements MCP protocol over SSE
"""
import json
import os
from flask import Flask, request, jsonify, Response
from flask_sse import sse
import requests


app = Flask(__name__)
app.config['REDIS_URL'] = 'redis://localhost:6379'

# MCP Protocol constants
MCP_VERSION = "2024-11-05"

# SSRF protection
BLOCKED_IP_RANGES = ["127.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.2", "192.168.", "169.254."]


def is_internal_ip(url):
    """Check if URL points to internal network"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        for blocked in BLOCKED_IP_RANGES:
            if host.startswith(blocked) or host in ["localhost"]:
                return True
        return False
    except:
        return True


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})


@app.route('/mcp', methods=['GET', 'POST'])
def mcp():
    """MCP Protocol endpoint"""
    if request.method == 'GET':
        # SSE connection for MCP
        return Response(
            event='message',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

    # Handle MCP JSON-RPC requests
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    method = data.get("method")
    params = data.get("params", {})
    msg_id = data.get("id")

    # Handle MCP methods
    if method == "initialize":
        result = {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {
                "name": "local-search",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {}
            }
        }
    elif method == "tools/list":
        # Return available tools
        result = {
            "tools": [
                {
                    "name": "search",
                    "description": "Search the web using SearXNG",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "search":
            query = arguments.get("query", "")
            try:
                # Call SearXNG API
                resp = requests.get(
                    f"http://localhost:8080/search",
                    params={"q": query, "format": "json"},
                    timeout=10
                )
                results = resp.json() if resp.status_code == 200 else []

                # Format results
                formatted = []
                for r in results.get("results", [])[:10]:
                    formatted.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", "")[:200]
                    })

                result = {"content": [{"type": "text", "text": json.dumps(formatted, ensure_ascii=False)}]}
            except Exception as e:
                result = {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    else:
        result = {"error": f"Unknown method: {method}"}

    return jsonify({
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": result
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=18880)

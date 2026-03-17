#!/usr/bin/env python3
"""
Playwright MCP Service
Provides web automation and scraping via HTTP API
"""
import json
import re
import base64
from urllib.parse import urlparse

from flask import Flask, request, jsonify
import requests


app = Flask(__name__)

# Note: This is a lightweight implementation
# For full Playwright integration, install: pip install playwright playwright-mcp

# SSRF protection: blocked IP ranges
BLOCKED_IP_RANGES = [
    "127.",  # localhost
    "10.",   # private
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",  # private
    "169.254.",  # link-local
]


def is_internal_ip(url):
    """Check if URL points to internal network"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False

        # Block localhost variants
        if host in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
            return True

        # Block private IP ranges
        for blocked in BLOCKED_IP_RANGES:
            if host.startswith(blocked):
                return True

        return False
    except Exception:
        return True


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/navigate', methods=['POST'])
def navigate():
    """Navigate to a URL and get content"""
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]

    # SSRF protection
    if is_internal_ip(url):
        return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

    # Basic validation
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL scheme"}), 400

    try:
        # Use requests for basic fetching (lightweight alternative)
        # For full Playwright: use playwright library
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()

        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
        title = title_match.group(1) if title_match else ""

        # Extract meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
        description = desc_match.group(1) if desc_match else ""

        return jsonify({
            "url": url,
            "title": title,
            "description": description,
            "status_code": response.status_code,
            "content_length": len(response.content)
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500


@app.route('/screenshot', methods=['POST'])
def screenshot():
    """Capture screenshot of a webpage"""
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]

    # SSRF protection
    if is_internal_ip(url):
        return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

    # For full screenshot: use Playwright
    # This is a placeholder that returns an error
    return jsonify({
        "error": "Screenshot requires Playwright installation",
        "url": url,
        "message": "Install playwright and use browser automation"
    }), 501


@app.route('/content', methods=['GET'])
def content():
    """Get content of last visited page"""
    return jsonify({"error": "No cached content"}), 404


@app.route('/click', methods=['POST'])
def click():
    """Click element on page"""
    data = request.get_json()

    if not data or "selector" not in data:
        return jsonify({"error": "No selector provided"}), 400

    return jsonify({"error": "Click requires Playwright"}), 501


@app.route('/fill', methods=['POST'])
def fill():
    """Fill form on page"""
    data = request.get_json()

    if not data or "form" not in data:
        return jsonify({"error": "No form data provided"}), 400

    return jsonify({"error": "Fill requires Playwright"}), 501


if __name__ == '__main__':
    # Disable SSL warnings for development
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    app.run(host='0.0.0.0', port=3100)

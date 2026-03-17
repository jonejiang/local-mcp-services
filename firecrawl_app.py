#!/usr/bin/env python3
"""
Firecrawl MCP Service
Provides document parsing and web scraping via HTTP API
"""
import json
import re
from urllib.parse import urlparse
from urllib.parse import urljoin

from flask import Flask, request, jsonify
import requests


app = Flask(__name__)

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
    "metadata.google.internal",  # GCP metadata
]


def is_internal_ip(url):
    """Check if URL points to internal network"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return True

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


def extract_text_from_html(html_content):
    """Extract text from HTML"""
    # Remove script and style elements
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_links(html_content, base_url):
    """Extract links from HTML"""
    links = []
    for match in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>', html_content, re.IGNORECASE):
        href = match.group(1)
        if href.startswith('http'):
            links.append(href)
        elif href.startswith('/'):
            links.append(urljoin(base_url, href))
    return links[:50]  # Limit to 50 links


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/crawl', methods=['POST'])
def crawl():
    """Crawl a URL and extract content"""
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]

    # SSRF protection
    if is_internal_ip(url):
        return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

    # Validate URL
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL scheme"}), 400

    try:
        response = requests.get(url, timeout=30, verify=False)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")

        # Handle HTML
        if "text/html" in content_type:
            html_content = response.text

            # Extract text
            text = extract_text_from_html(html_content)

            # Extract links
            links = extract_links(html_content, url)

            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
            title = title_match.group(1) if title_match else ""

            # Extract meta description
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            description = desc_match.group(1) if desc_match else ""

            return jsonify({
                "url": url,
                "title": title,
                "description": description,
                "content": text,
                "links": links,
                "content_type": content_type
            }), 200

        # Handle plain text
        elif "text/plain" in content_type:
            return jsonify({
                "url": url,
                "content": response.text,
                "content_type": content_type
            }), 200

        # Other content types
        return jsonify({
            "url": url,
            "content_type": content_type,
            "message": "Unsupported content type"
        }), 415

    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500


@app.route('/extract', methods=['POST'])
def extract():
    """Extract structured data from URL"""
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]

    # SSRF protection
    if is_internal_ip(url):
        return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

    try:
        # For now, return basic crawl
        response = requests.get(url, timeout=30, verify=False)

        text = extract_text_from_html(response.text)

        return jsonify({
            "url": url,
            "text": text,
            "prompt": data.get("prompt", "")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/parse', methods=['POST'])
def parse():
    """Parse document (PDF, DOCX, etc.)"""
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]

    # SSRF protection
    if is_internal_ip(url):
        return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

    return jsonify({
        "error": "Document parsing requires firecrawl SDK",
        "url": url
    }), 501


@app.route('/scrape', methods=['POST'])
def scrape():
    """Scrape with schema"""
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "No URL provided"}), 400

    url = data["url"]

    # SSRF protection
    if is_internal_ip(url):
        return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

    # Basic scraping with optional schema
    try:
        response = requests.get(url, timeout=30, verify=False)
        text = extract_text_from_html(response.text)

        schema = data.get("schema", {})

        return jsonify({
            "url": url,
            "data": {
                "content": text,
                "schema": schema
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Disable SSL warnings for development
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    app.run(host='0.0.0.0', port=8002)

#!/usr/bin/env python3
"""
EasyOCR MCP Service
Provides OCR functionality via HTTP API
"""
import base64
import io
import json
import re
import requests
from urllib.parse import urlparse

from flask import Flask, request, jsonify
import easyocr
from PIL import Image


app = Flask(__name__)

# Initialize EasyOCR reader (English and Chinese)
# Load lazily to improve startup time
reader = None

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
        return True  # Block on any error


def get_reader():
    """Get or create EasyOCR reader"""
    global reader
    if reader is None:
        reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
    return reader


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/ocr', methods=['POST'])
def ocr():
    """OCR endpoint"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    image_data = None

    # Handle URL input
    if "url" in data:
        url = data["url"]

        # SSRF protection
        if is_internal_ip(url):
            return jsonify({"error": "SSRF protection: blocked internal URL"}), 403

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return jsonify({"error": "Failed to fetch image"}), 400
            image_data = response.content
        except Exception as e:
            return jsonify({"error": f"Failed to fetch image: {str(e)}"}), 400

    # Handle base64 input
    elif "image" in data:
        try:
            image_data = base64.b64decode(data["image"])
        except Exception as e:
            return jsonify({"error": f"Invalid base64: {str(e)}"}), 400

    else:
        return jsonify({"error": "No image or url provided"}), 400

    if not image_data:
        return jsonify({"error": "No image data"}), 400

    try:
        # Load image
        image = Image.open(io.BytesIO(image_data))

        # Perform OCR
        reader = get_reader()
        results = reader.readtext(io.BytesIO(image_data))

        # Format results
        text_results = []
        for bbox, text, confidence in results:
            text_results.append({
                "text": text,
                "confidence": float(confidence)
            })

        full_text = " ".join([r["text"] for r in text_results])

        return jsonify({
            "text": full_text,
            "results": text_results
        }), 200

    except Exception as e:
        return jsonify({"error": f"OCR failed: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

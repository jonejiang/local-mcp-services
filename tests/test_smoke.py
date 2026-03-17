"""
Smoke Tests - Quick validation of basic functionality
"""
import pytest
import requests


class TestSmokeTests:
    """Quick smoke tests for all services"""

    @pytest.mark.parametrize("port,service", [
        (18880, "SearXNG"),
        (18881, "EasyOCR"),
        (18882, "Playwright"),
        (18883, "Firecrawl"),
    ])
    def test_service_health(self, port, service):
        """Verify service is accessible"""
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        assert response.status_code == 200, f"{service} health check failed"

    @pytest.mark.parametrize("port,service", [
        (18880, "SearXNG"),
        (18881, "EasyOCR"),
        (18882, "Playwright"),
        (18883, "Firecrawl"),
    ])
    def test_service_basic_function(self, port, service):
        """Verify basic function works"""
        if port == 18880:  # SearXNG
            response = requests.post(
                f"http://localhost:{port}/search",
                json={"q": "test"},
                timeout=30
            )
        elif port == 18881:  # EasyOCR
            response = requests.post(
                f"http://localhost:{port}/ocr",
                json={"url": "https://httpbin.org/image/png"},
                timeout=60
            )
        elif port == 18882:  # Playwright
            response = requests.post(
                f"http://localhost:{port}/navigate",
                json={"url": "https://example.com"},
                timeout=30
            )
        else:  # Firecrawl
            response = requests.post(
                f"http://localhost:{port}/crawl",
                json={"url": "https://example.com"},
                timeout=60
            )

        # Should not return 500
        assert response.status_code < 500, \
            f"{service} returned server error"

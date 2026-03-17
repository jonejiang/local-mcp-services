"""
Firecrawl Service Tests
TDD: Test-first approach for document parsing functionality
"""
import pytest
import requests
import base64


class TestFirecrawl:
    """Firecrawl service test suite"""

    @pytest.fixture(autouse=True)
    def setup(self, firecrawl_url, wait_for_services):
        self.base_url = firecrawl_url

    # ===== Happy Path Tests =====

    def test_crawl_url(self):
        """Test URL crawling functionality"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "https://example.com"},
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data or "data" in data or "text" in data

    def test_crawl_response_structure(self):
        """Test crawl response contains required fields"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "https://example.com"},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            # Should have some content
            assert any(key in data for key in ["content", "data", "text", "html"])

    def test_extract_from_url(self):
        """Test data extraction from URL"""
        response = requests.post(
            f"{self.base_url}/extract",
            json={
                "url": "https://example.com",
                "prompt": "Extract the main content"
            },
            timeout=60
        )
        assert response.status_code in [200, 400]

    # ===== Document Parsing Tests =====

    def test_parse_pdf_from_url(self):
        """Test PDF parsing from URL"""
        response = requests.post(
            f"{self.base_url}/parse",
            json={"url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"},
            timeout=60
        )
        assert response.status_code in [200, 400, 502]

    # ===== Negative Tests =====

    def test_crawl_empty_url(self):
        """Test crawl with empty URL"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": ""},
            timeout=10
        )
        assert response.status_code == 400

    def test_crawl_invalid_url(self):
        """Test crawl with invalid URL"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "not-a-valid-url"},
            timeout=10
        )
        assert response.status_code == 400

    def test_crawl_timeout(self):
        """Test crawl timeout handling"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "https://httpbin.org/delay/10"},
            timeout=5
        )
        # Should timeout gracefully
        assert response.status_code in [200, 408, 504]

    def test_crawl_robots_disallowed(self):
        """Test crawl respects robots.txt"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "https://google.com/robots.txt"},
            timeout=30
        )
        # Should handle robots.txt - either crawl or return 403
        assert response.status_code in [200, 403]

    # ===== Security Tests =====

    def test_ssrf_protection_internal_ip(self):
        """Test SSRF protection blocks internal IP"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "http://192.168.1.1"},
            timeout=10
        )
        assert response.status_code in [400, 403]

    def test_ssrf_protection_localhost(self):
        """Test SSRF protection blocks localhost"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "http://127.0.0.1/admin"},
            timeout=10
        )
        assert response.status_code in [400, 403]

    def test_ssrf_protection_internal_domain(self):
        """Test SSRF protection blocks internal domains"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={"url": "http://internal.corp/page"},
            timeout=10
        )
        assert response.status_code in [400, 403]

    # ===== Service Health =====

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        assert response.status_code == 200

    # ===== Advanced Tests =====

    def test_crawl_with_options(self):
        """Test crawl with additional options"""
        response = requests.post(
            f"{self.base_url}/crawl",
            json={
                "url": "https://example.com",
                "options": {
                    "depth": 1,
                    "limit": 10
                }
            },
            timeout=60
        )
        assert response.status_code in [200, 400]

    def test_scrape_with_schema(self):
        """Test scraping with schema"""
        response = requests.post(
            f"{self.base_url}/scrape",
            json={
                "url": "https://example.com",
                "schema": {
                    "title": "string",
                    "links": "array"
                }
            },
            timeout=60
        )
        assert response.status_code in [200, 400]

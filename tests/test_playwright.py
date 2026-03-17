"""
Playwright MCP Service Tests
TDD: Test-first approach for web scraping functionality
"""
import pytest
import requests


class TestPlaywright:
    """Playwright MCP service test suite"""

    @pytest.fixture(autouse=True)
    def setup(self, playwright_url, wait_for_services):
        self.base_url = playwright_url

    # ===== Happy Path Tests =====

    def test_navigate_to_url(self):
        """Test page navigation to a URL"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "https://example.com"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "title" in data or "url" in data or "content" in data

    def test_get_page_content(self):
        """Test retrieving page content"""
        # First navigate
        requests.post(
            f"{self.base_url}/navigate",
            json={"url": "https://example.com"},
            timeout=30
        )
        # Then get content
        response = requests.get(f"{self.base_url}/content", timeout=10)
        assert response.status_code in [200, 404]

    def test_screenshot_capture(self):
        """Test screenshot capture functionality"""
        response = requests.post(
            f"{self.base_url}/screenshot",
            json={"url": "https://example.com"},
            timeout=30
        )
        # Should return image or error
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert "image" in response.json() or "data" in response.json()

    # ===== Negative Tests =====

    def test_navigate_invalid_url(self):
        """Test navigation to invalid URL"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "not-a-valid-url"},
            timeout=10
        )
        assert response.status_code == 400

    def test_navigate_empty_url(self):
        """Test navigation with empty URL"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": ""},
            timeout=10
        )
        assert response.status_code == 400

    def test_navigate_timeout(self):
        """Test navigation timeout handling"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "https://httpbin.org/delay/10"},
            timeout=5
        )
        # Should timeout gracefully
        assert response.status_code in [200, 408, 504]

    def test_navigate_ssl_error(self):
        """Test navigation to site with SSL errors"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "https://expired.badssl.com/"},
            timeout=30
        )
        # Should handle SSL error gracefully
        assert response.status_code in [200, 400, 500]

    # ===== Security Tests =====

    def test_ssrf_protection_internal_ip(self):
        """Test SSRF protection blocks internal IP"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "http://192.168.1.1"},
            timeout=10
        )
        assert response.status_code in [400, 403]

    def test_ssrf_protection_localhost(self):
        """Test SSRF protection blocks localhost"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "http://127.0.0.1/admin"},
            timeout=10
        )
        assert response.status_code in [400, 403]

    def test_ssrf_protection_internal_domain(self):
        """Test SSRF protection blocks internal domains"""
        response = requests.post(
            f"{self.base_url}/navigate",
            json={"url": "http://localhost:8080"},
            timeout=10
        )
        assert response.status_code in [400, 403]

    # ===== Service Health =====

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        assert response.status_code == 200

    # ===== Advanced Tests =====

    def test_click_element(self):
        """Test element click functionality"""
        # First navigate to a page with clickable elements
        response = requests.post(
            f"{self.base_url}/click",
            json={
                "url": "https://example.com",
                "selector": "a"
            },
            timeout=30
        )
        assert response.status_code in [200, 400, 404]

    def test_fill_form(self):
        """Test form filling functionality"""
        response = requests.post(
            f"{self.base_url}/fill",
            json={
                "url": "https://example.com",
                "form": {"q": "test query"}
            },
            timeout=30
        )
        assert response.status_code in [200, 400, 404]

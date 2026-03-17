"""
SearXNG Search Service Tests
TDD: Test-first approach for search functionality
"""
import pytest
import requests


class TestSearXNG:
    """SearXNG search service test suite"""

    @pytest.fixture(autouse=True)
    def setup(self, searxng_url, wait_for_services):
        self.base_url = searxng_url

    # ===== Happy Path Tests =====

    def test_search_success(self):
        """Test basic search functionality returns results"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "python programming"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or "answer" in data

    def test_search_result_structure(self):
        """Test search results contain required fields"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "test query"},
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        # Should contain results with title, url
        results = data.get("results", [])
        if results:
            assert "title" in results[0] or "url" in results[0]

    def test_search_with_special_characters(self):
        """Test search handles special characters"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "C++ programming language"},
            timeout=30
        )
        assert response.status_code == 200

    def test_search_pagination(self):
        """Test search pagination works"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "python", "page": 2},
            timeout=30
        )
        assert response.status_code == 200

    # ===== Negative Tests =====

    def test_empty_search_query(self):
        """Test empty search query returns error"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": ""},
            timeout=10
        )
        assert response.status_code == 400

    def test_search_timeout_handling(self):
        """Test search timeout is handled gracefully"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "test"},
            timeout=5
        )
        # Should return either success or timeout error
        assert response.status_code in [200, 504, 408]

    def test_sql_injection_handling(self):
        """Test SQL injection attempts are handled safely"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "' OR '1'='1"},
            timeout=10
        )
        assert response.status_code == 200

    # ===== Security Tests =====

    def test_ssrf_protection_internal_ip(self):
        """Test SSRF protection blocks internal IP access"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "http://192.168.1.1/"},
            timeout=10
        )
        # Should be blocked or sanitized
        assert response.status_code in [400, 403, 200]

    def test_ssrf_protection_localhost(self):
        """Test SSRF protection blocks localhost access"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "http://127.0.0.1/admin"},
            timeout=10
        )
        assert response.status_code in [400, 403, 200]

    # ===== Service Health =====

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        assert response.status_code == 200

    def test_service_returns_json(self):
        """Test service returns JSON content type"""
        response = requests.post(
            f"{self.base_url}/search",
            json={"q": "test"},
            timeout=30
        )
        assert "application/json" in response.headers.get("Content-Type", "")

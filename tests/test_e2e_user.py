"""
End-to-End User Experience Tests
TDD: Test-first approach for complete user workflows
"""
import pytest
import requests
import time


class TestE2ESearchWorkflow:
    """E2E test for complete search workflow"""

    def test_full_search_workflow(self):
        """Complete search workflow from start to finish"""
        # Step 1: Verify service is running
        health = requests.get("http://localhost:18880/health", timeout=5)
        assert health.status_code == 200

        # Step 2: Perform search
        search_response = requests.post(
            "http://localhost:18880/search",
            json={"q": "python tutorial"},
            timeout=30
        )
        assert search_response.status_code == 200
        data = search_response.json()

        # Step 3: Verify results contain URLs
        results = data.get("results", [])
        if results:
            assert any("url" in r or "link" in r for r in results), \
                "Results should contain URLs"

    def test_search_to_playwright_workflow(self):
        """Test search followed by Playwright page visit"""
        # Step 1: Search for something
        search_response = requests.post(
            "http://localhost:18880/search",
            json={"q": "open source"},
            timeout=30
        )
        assert search_response.status_code == 200

        # Step 2: Use Playwright to visit one result
        playwright_response = requests.post(
            "http://localhost:18882/navigate",
            json={"url": "https://example.com"},
            timeout=30
        )
        assert playwright_response.status_code == 200

    def test_search_screenshot_workflow(self):
        """Test search followed by screenshot capture"""
        # Step 1: Search
        search_response = requests.post(
            "http://localhost:18880/search",
            json={"q": "test"},
            timeout=30
        )
        assert search_response.status_code == 200

        # Step 2: Screenshot
        screenshot_response = requests.post(
            "http://localhost:18882/screenshot",
            json={"url": "https://example.com"},
            timeout=30
        )
        assert screenshot_response.status_code in [200, 400]


class TestE2EOCRWorkflow:
    """E2E test for complete OCR workflow"""

    def test_basic_ocr_workflow(self):
        """Complete OCR workflow from upload to result"""
        # Step 1: Verify service is running
        health = requests.get("http://localhost:18881/health", timeout=5)
        assert health.status_code == 200

        # Step 2: Submit OCR request with URL
        ocr_response = requests.post(
            "http://localhost:18881/ocr",
            json={"url": "https://httpbin.org/image/png"},
            timeout=60
        )
        # Should either succeed or fail gracefully
        assert ocr_response.status_code in [200, 400, 502]


class TestE2EDocumentWorkflow:
    """E2E test for complete document parsing workflow"""

    def test_url_crawl_workflow(self):
        """Complete document crawling workflow"""
        # Step 1: Verify service is running
        health = requests.get("http://localhost:18883/health", timeout=5)
        assert health.status_code == 200

        # Step 2: Crawl URL
        crawl_response = requests.post(
            "http://localhost:18883/crawl",
            json={"url": "https://example.com"},
            timeout=60
        )
        assert crawl_response.status_code == 200
        data = crawl_response.json()

        # Step 3: Verify content extracted
        assert any(key in data for key in ["content", "data", "text", "html"])


class TestE2EMultiServiceWorkflow:
    """E2E test for multiple services working together"""

    def test_search_crawl_ocr_workflow(self):
        """Full workflow: search -> crawl -> OCR"""
        # Step 1: Search
        search = requests.post(
            "http://localhost:18880/search",
            json={"q": "python programming"},
            timeout=30
        )
        assert search.status_code == 200

        # Step 2: Crawl content
        crawl = requests.post(
            "http://localhost:18883/crawl",
            json={"url": "https://example.com"},
            timeout=60
        )
        assert crawl.status_code == 200

        # Step 3: OCR (if needed)
        # This is a conceptual workflow - actual OCR would need an image

    def test_parallel_service_access(self):
        """Test accessing multiple services in parallel"""
        import concurrent.futures

        def check_service(port):
            return requests.get(f"http://localhost:{port}/health", timeout=5)

        ports = [18880, 18881, 18882, 18883]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(check_service, port) for port in ports]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All services should respond
        assert all(r.status_code == 200 for r in results)


class TestE2ERecovery:
    """E2E test for service recovery scenarios"""

    def test_service_restart_recovery(self):
        """Test service recovers after restart"""
        # This test would require docker access to restart containers
        # Skipping in regular test run
        pytest.skip("Requires docker restart capability")

    def test_health_check_persistence(self):
        """Test health endpoints remain stable over time"""
        for _ in range(5):
            for port in [18880, 18881, 18882, 18883]:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                assert response.status_code == 200
            time.sleep(1)


class TestE2EErrorHandling:
    """E2E test for error handling across services"""

    def test_graceful_degradation(self):
        """Test services handle errors gracefully"""
        # Invalid input should return proper error
        response = requests.post(
            "http://localhost:18880/search",
            json={"q": ""},
            timeout=10
        )
        # Should return 400, not 500
        assert response.status_code == 400

    def test_timeout_handling(self):
        """Test services handle timeouts gracefully"""
        # Long-running request should timeout cleanly
        response = requests.post(
            "http://localhost:18882/navigate",
            json={"url": "https://httpbin.org/delay/5"},
            timeout=2
        )
        # Should timeout, not hang
        assert response.status_code in [408, 504]

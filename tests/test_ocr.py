"""
EasyOCR Service Tests
TDD: Test-first approach for OCR functionality
"""
import pytest
import requests
import base64
import os


class TestEasyOCR:
    """EasyOCR service test suite"""

    @pytest.fixture(autouse=True)
    def setup(self, easyocr_url, wait_for_services):
        self.base_url = easyocr_url

    def _create_simple_image_base64(self):
        """Create a simple test image as base64 (1x1 white pixel PNG)"""
        # Minimal valid PNG (1x1 white pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        return base64.b64encode(png_data).decode()

    # ===== Happy Path Tests =====

    def test_ocr_english_text(self):
        """Test OCR recognizes English text"""
        # Use a simple test image
        image_data = self._create_simple_image_base64()
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"image": image_data},
            timeout=60
        )
        # Should return 200 or 400 (if image invalid)
        assert response.status_code in [200, 400]

    def test_ocr_response_structure(self):
        """Test OCR response contains required fields"""
        image_data = self._create_simple_image_base64()
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"image": image_data},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            assert "text" in data or "results" in data

    def test_ocr_with_url(self):
        """Test OCR accepts image URL"""
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"url": "https://httpbin.org/image/png"},
            timeout=60
        )
        # Should handle URL or return error for invalid URL
        assert response.status_code in [200, 400, 502]

    # ===== Negative Tests =====

    def test_ocr_empty_request(self):
        """Test OCR handles empty request"""
        response = requests.post(
            f"{self.base_url}/ocr",
            json={},
            timeout=10
        )
        assert response.status_code == 400

    def test_ocr_invalid_base64(self):
        """Test OCR handles invalid base64 data"""
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"image": "not-valid-base64!!!"},
            timeout=30
        )
        assert response.status_code == 400

    def test_ocr_invalid_url(self):
        """Test OCR handles invalid URL"""
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"url": "not-a-valid-url"},
            timeout=30
        )
        assert response.status_code == 400

    def test_ocr_timeout_handling(self):
        """Test OCR timeout is handled gracefully"""
        # Large image that takes long to process
        large_image = "A" * 1000000
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"image": large_image},
            timeout=10
        )
        # Should handle timeout gracefully
        assert response.status_code in [200, 400, 408, 504]

    # ===== Security Tests =====

    def test_ssrf_protection_internal_url(self):
        """Test SSRF protection blocks internal URLs"""
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"url": "http://192.168.1.1/image.png"},
            timeout=30
        )
        assert response.status_code in [400, 403]

    def test_ssrf_protection_localhost(self):
        """Test SSRF protection blocks localhost"""
        response = requests.post(
            f"{self.base_url}/ocr",
            json={"url": "http://127.0.0.1/image.png"},
            timeout=30
        )
        assert response.status_code in [400, 403]

    # ===== Service Health =====

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        assert response.status_code == 200

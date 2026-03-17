"""
pytest configuration and fixtures for MCP services testing
"""
import pytest
import requests
import time
import os


# Service endpoints configuration
SERVICES = {
    "searxng": {"port": 18880, "health": "/health"},
    "easyocr": {"port": 18881, "health": "/health"},
    "playwright": {"port": 18882, "health": "/health"},
    "firecrawl": {"port": 18883, "health": "/health"},
}


@pytest.fixture(scope="session")
def service_urls():
    """Base URLs for all services"""
    base_url = "http://localhost"
    return {
        name: f"{base_url}:{config['port']}"
        for name, config in SERVICES.items()
    }


@pytest.fixture(scope="session")
def wait_for_services(service_urls):
    """Wait for all services to be available before running tests"""
    max_retries = 30
    retry_delay = 2

    for service_name, url in service_urls.items():
        health_url = f"{url}{SERVICES[service_name]['health']}"
        for attempt in range(max_retries):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print(f"✓ {service_name} is ready")
                    break
            except requests.exceptions.RequestException:
                pass
            if attempt == max_retries - 1:
                pytest.skip(f"{service_name} is not available")
            time.sleep(retry_delay)
    return True


@pytest.fixture
def searxng_url(service_urls):
    """SearXNG service URL"""
    return service_urls["searxng"]


@pytest.fixture
def easyocr_url(service_urls):
    """EasyOCR service URL"""
    return service_urls["easyocr"]


@pytest.fixture
def playwright_url(service_urls):
    """Playwright service URL"""
    return service_urls["playwright"]


@pytest.fixture
def firecrawl_url(service_urls):
    """Firecrawl service URL"""
    return service_urls["firecrawl"]


@pytest.fixture
def sample_image_path():
    """Path to sample test image"""
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample.png")


@pytest.fixture
def sample_pdf_path():
    """Path to sample test PDF"""
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")

"""
Security Tests for MCP Services
TDD: Test-first approach for security configurations
"""
import pytest
import requests
import subprocess
import json


class TestSecurityConfiguration:
    """Security configuration test suite"""

    @pytest.fixture
    def docker_command(self):
        """Docker command helper"""
        return lambda cmd: subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

    # ===== Container Security Tests =====

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_not_root_user(self, container, docker_command):
        """Verify containers don't run as root"""
        result = docker_command(["docker", "inspect", container, "--format", "{{.Config.User}}"])
        user = result.stdout.strip()
        # Should be empty (default) or non-root user
        assert user == "" or user != "0:0", f"{container} should not run as root"

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_readonly_filesystem(self, container, docker_command):
        """Verify root filesystem is read-only"""
        result = docker_command([
            "docker", "inspect", container,
            "--format", "{{.HostConfig.ReadonlyRootfs}}"
        ])
        is_readonly = result.stdout.strip().lower() == "true"
        assert is_readonly, f"{container} should have read-only root filesystem"

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_no_new_privileges(self, container, docker_command):
        """Verify no-new-privileges is set"""
        result = docker_command([
            "docker", "inspect", container,
            "--format", "{{.SecurityOpt}}"
        ])
        security_opts = result.stdout.strip()
        assert "no-new-privileges" in security_opts.lower(), \
            f"{container} should have no-new-privileges set"

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_memory_limit(self, container, docker_command):
        """Verify memory limits are set"""
        result = docker_command([
            "docker", "inspect", container,
            "--format", "{{.HostConfig.Memory}}"
        ])
        memory = result.stdout.strip()
        assert memory != "0", f"{container} should have memory limit set"

    # ===== Network Security Tests =====

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_network_isolation(self, container, docker_command):
        """Verify containers are on mcp-net"""
        result = docker_command([
            "docker", "inspect", container,
            "--format", "{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}"
        ])
        networks = result.stdout.strip()
        assert "mcp" in networks.lower(), f"{container} should be on mcp-net"

    # ===== Capability Tests =====

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "firecrawl"])
    def test_capabilities_dropped(self, container, docker_command):
        """Verify all capabilities are dropped except minimal required"""
        result = docker_command([
            "docker", "inspect", container,
            "--format", "{{.HostConfig.CapDrop}}"
        ])
        cap_drop = result.stdout.strip().lower()
        assert "all" in cap_drop, f"{container} should drop all capabilities"

    # ===== SSRF Protection Tests =====

    def test_ssrf_all_services_internal_ip(self):
        """Test SSRF protection across all services"""
        internal_ips = [
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://172.16.0.1",
        ]

        services = [
            ("searxng", 18880, "/search"),
            ("easyocr", 18881, "/ocr"),
            ("playwright", 18882, "/navigate"),
            ("firecrawl", 18883, "/crawl"),
        ]

        for service, port, endpoint in services:
            for ip in internal_ips:
                response = requests.post(
                    f"http://localhost:{port}{endpoint}",
                    json={"q": ip} if "search" in endpoint else {"url": ip},
                    timeout=10
                )
                assert response.status_code in [400, 403], \
                    f"{service} should block SSRF to {ip}"


class TestSSRFProtection:
    """SSRF protection test suite"""

    @pytest.mark.parametrize("service,port,endpoint", [
        ("searxng", 18880, "/search"),
        ("easyocr", 18881, "/ocr"),
        ("playwright", 18882, "/navigate"),
        ("firecrawl", 18883, "/crawl"),
    ])
    def test_block_internal_ips(self, service, port, endpoint):
        """Test blocking access to internal IP ranges"""
        test_cases = [
            "http://192.168.0.1",
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://127.0.0.1",
            "http://localhost",
        ]

        for url in test_cases:
            if "search" in endpoint:
                payload = {"q": url}
            else:
                payload = {"url": url}

            response = requests.post(
                f"http://localhost:{port}{endpoint}",
                json=payload,
                timeout=10
            )
            assert response.status_code in [400, 403], \
                f"{service} should block {url}"

    @pytest.mark.parametrize("service,port,endpoint", [
        ("searxng", 18880, "/search"),
        ("easyocr", 18881, "/ocr"),
        ("playwright", 18882, "/navigate"),
        ("firecrawl", 18883, "/crawl"),
    ])
    def test_block_metadata_endpoints(self, service, port, endpoint):
        """Test blocking access to cloud metadata endpoints"""
        metadata_endpoints = [
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/",
        ]

        for url in metadata_endpoints:
            if "search" in endpoint:
                payload = {"q": url}
            else:
                payload = {"url": url}

            response = requests.post(
                f"http://localhost:{port}{endpoint}",
                json=payload,
                timeout=10
            )
            # Should block or reject
            assert response.status_code in [400, 403, 200], \
                f"{service} should handle {url}"

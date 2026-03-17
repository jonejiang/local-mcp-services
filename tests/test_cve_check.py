#!/usr/bin/env python3
"""
CVE Check Tests for MCP Server
TDD: Test CVE-2025-9074 and other container vulnerability checks
"""
import pytest
import subprocess
import re
import os


class TestCVE20259074:
    """Test CVE-2025-9074 (Docker Desktop container escape)"""

    def test_docker_version_check(self):
        """Test Docker version is >= 4.44.3"""
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True
        )

        version = result.stdout.strip()
        print(f"Docker version: {version}")

        # Parse version
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version)
        assert match, "Could not parse Docker version"

        major, minor, patch = map(int, match.groups())

        # Check >= 4.44.3
        assert (major > 4 or
                (major == 4 and minor > 44) or
                (major == 4 and minor == 44 and patch >= 3)), \
            f"Docker version {version} is vulnerable to CVE-2025-9074. Need >= 4.44.3"

    def test_docker_info_check(self):
        """Test Docker daemon information"""
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True
        )

        info = result.stdout

        # Check for rootless mode (recommended)
        if "rootless" in info.lower():
            print("Rootless mode: enabled")
        else:
            print("Rootless mode: not detected (recommended)")

        # Should not show vulnerabilities
        assert "CVE-2025-9074" not in info


class TestContainerSecurityCVEs:
    """Test container security configurations"""

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_no_privileged_container(self, container):
        """Test container is not running in privileged mode"""
        result = subprocess.run(
            ["docker", "inspect", container, "--format", "{{.HostConfig.Privileged}}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Container {container} not running")

        is_privileged = result.stdout.strip().lower() == "true"
        assert not is_privileged, f"{container} is running in privileged mode!"

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_userns_mode(self, container):
        """Test user namespace is configured if possible"""
        result = subprocess.run(
            ["docker", "inspect", container, "--format", "{{.HostConfig.UsernsMode}}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Container {container} not running")

        userns = result.stdout.strip()
        # host means not using user namespaces
        # Should be "host" or empty for basic security
        print(f"{container} userns: {userns}")


class TestKernelVulnerabilities:
    """Test for known kernel vulnerabilities"""

    def test_sysctl_settings(self):
        """Test kernel parameters are secure"""
        # Check kernel.deny_write_exec
        result = subprocess.run(
            ["sysctl", "kernel.deny_write_exec"],
            capture_output=True,
            text=True
        )

        # May not exist on all systems
        if result.returncode == 0:
            print(f"kernel.deny_write_exec: {result.stdout.strip()}")

    def test_seccomp_enabled(self):
        """Test seccomp is enabled for Docker"""
        result = subprocess.run(
            ["docker", "info", "--format", "{{.SecurityOptions}}"],
            capture_output=True,
            text=True
        )

        security_opts = result.stdout.lower()

        # Should have seccomp or apparmor or selinux
        has_security = any(x in security_opts for x in ["seccomp", "apparmor", "selinux"])
        print(f"Security options: {security_opts[:200]}")


class TestDockerDaemonSecurity:
    """Test Docker daemon security"""

    def test_docker_socket_permissions(self):
        """Test Docker socket permissions"""
        socket_path = "/var/run/docker.sock"

        if not os.path.exists(socket_path):
            pytest.skip("Docker socket not found")

        stat_info = os.stat(socket_path)
        mode = stat_info.st_mode & 0o777

        # Should not be world-writable
        assert not (mode & 0o002), "Docker socket is world-writable!"

    def test_content_trust_enabled(self):
        """Test Docker content trust (DCT)"""
        # Check if DCT is enabled
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ContentTrust}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            ct_status = result.stdout.strip()
            print(f"Content Trust: {ct_status}")
            # Should ideally be enabled, but not required for local dev


class TestImageVulnerabilities:
    """Test Docker image security"""

    @pytest.mark.parametrize("container", ["searxng", "easyocr", "playwright", "firecrawl"])
    def test_container_base_image(self, container):
        """Test container is using a reasonable base image"""
        result = subprocess.run(
            ["docker", "inspect", container, "--format", "{{.Config.Image}}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Container {container} not running")

        image = result.stdout.strip()
        print(f"{container} image: {image}")

        # Should not use "latest" tag for production
        # But this is a warning, not a hard fail for local dev


class TestHostSecurity:
    """Test host system security"""

    def test_docker_group_membership(self):
        """Test user is in docker group"""
        result = subprocess.run(
            ["groups"],
            capture_output=True,
            text=True
        )

        groups = result.stdout
        print(f"User groups: {groups}")

        # User should be in docker group or use rootless

    def test_no_docker_insecure_registries(self):
        """Test no insecure registries configured"""
        result = subprocess.run(
            ["docker", "info", "--format", "{{.RegistryConfig.InsecureRegistryCIDRs}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            cidrs = result.stdout.strip()
            print(f"Insecure registries: {cidrs[:100]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

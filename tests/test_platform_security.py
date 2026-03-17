#!/usr/bin/env python3
"""
Platform Security Tests for MCP Server
TDD: Test platform-specific security configurations
"""
import pytest
import subprocess
import platform
import os


class TestLinuxSecurity:
    """Linux-specific security tests"""

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
    def test_selinux_status(self):
        """Test SELinux status"""
        result = subprocess.run(
            ["getenforce"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            status = result.stdout.strip()
            print(f"SELinux: {status}")
            # Enforcing is best, Permissive is OK for development

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
    def test_apparmor_status(self):
        """Test AppArmor status"""
        result = subprocess.run(
            ["aa-status"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"AppArmor: enabled")
        else:
            print(f"AppArmor: not available")

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
    def test_firewall_status(self):
        """Test firewall status"""
        # Check ufw
        result = subprocess.run(
            ["ufw", "status"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"UFW: {result.stdout.split()[1]}")

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux only")
    def test_sysctl_network_hardening(self):
        """Test network hardening sysctls"""
        sysctls = [
            "net.ipv4.ip_forward",
            "net.ipv4.conf.all.rp_filter",
            "net.ipv4.icmp_echo_ignore_broadcasts",
            "net.ipv4.conf.all.accept_redirects",
            "net.ipv4.conf.all.send_redirects",
        ]

        for sysctl in sysctls:
            result = subprocess.run(
                ["sysctl", "-n", sysctl],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                value = result.stdout.strip()
                print(f"{sysctl} = {value}")


class TestMacOSSecurity:
    """macOS-specific security tests"""

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_firewall_status(self):
        """Test macOS firewall"""
        result = subprocess.run(
            ["defaults", "read", "/Library/Preferences/com.apple.alf", "globalstate"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            state = result.stdout.strip()
            firewall_states = {0: "Off", 1: "On (Block all)", 2: "On (Allow signed)"}
            print(f"Firewall: {firewall_states.get(int(state), 'Unknown')}")

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_gatekeeper_status(self):
        """Test Gatekeeper status"""
        result = subprocess.run(
            ["spctl", "--status"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Gatekeeper: {result.stdout.strip()}")

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_filevault_status(self):
        """Test FileVault status"""
        result = subprocess.run(
            ["fdesetup", "status"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"FileVault: {result.stdout.split()[0]}")


class TestDockerSecurity:
    """Docker-specific security tests"""

    def test_docker_version(self):
        """Test Docker version"""
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        print(f"Docker: {result.stdout.strip()}")

    def test_docker_sock_permissions(self):
        """Test Docker socket permissions"""
        sock_path = "/var/run/docker.sock"

        if not os.path.exists(sock_path):
            pytest.skip("Docker socket not found")

        stat_info = os.stat(sock_path)
        mode = stat_info.st_mode & 0o777

        # Owner should have read/write
        assert mode & 0o600, "Docker socket permissions too open"

    def test_docker_daemon_config(self):
        """Test Docker daemon configuration"""
        daemon_files = [
            "/etc/docker/daemon.json",
            os.path.expanduser("~/.docker/daemon.json")
        ]

        for f in daemon_files:
            if os.path.exists(f):
                print(f"Found daemon config: {f}")
                with open(f) as fp:
                    content = fp.read()
                    # Basic check - don't expose secrets
                    assert "password" not in content.lower()


class TestNetworkSecurity:
    """Network security tests"""

    def test_port_bindings(self):
        """Test allowed port bindings"""
        ports = [18880, 18881, 18882, 18883]

        for port in ports:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"Port {port}: {result.stdout.split()[9] if result.stdout else 'LISTEN'}")

    def test_listening_services(self):
        """Test listening services"""
        result = subprocess.run(
            ["ss", "-tuln"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Listening ports (sample):")
            lines = result.stdout.split("\n")[:10]
            for line in lines:
                print(f"  {line}")


class TestProcessSecurity:
    """Process security tests"""

    def test_running_as_root(self):
        """Test running as root"""
        is_root = os.geteuid() == 0
        print(f"Running as root: {is_root}")

        if is_root:
            print("WARNING: Running as root is not recommended for security")

    def test_process_limits(self):
        """Test process limits"""
        result = subprocess.run(
            ["ulimit", "-a"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Process limits (sample):")
            lines = result.stdout.split("\n")[:5]
            for line in lines:
                print(f"  {line}")


class TestFileSystemSecurity:
    """File system security tests"""

    def test_home_directory_permissions(self):
        """Test home directory permissions"""
        home = os.path.expanduser("~")
        stat_info = os.stat(home)
        mode = stat_info.st_mode & 0o777

        # Should be 700 or similar
        print(f"Home directory ({home}): {oct(mode)}")

    def test_ssh_permissions(self):
        """Test SSH directory permissions"""
        ssh_dir = os.path.expanduser("~/.ssh")

        if os.path.exists(ssh_dir):
            stat_info = os.stat(ssh_dir)
            mode = stat_info.st_mode & 0o777

            # Should be 700
            assert mode & 0o077 == 0, "SSH directory is too open!"

            # Check key files
            for f in ["id_rsa", "id_ed25519"]:
                key_path = os.path.join(ssh_dir, f)
                if os.path.exists(key_path):
                    key_stat = os.stat(key_path)
                    key_mode = key_stat.st_mode & 0o777

                    # Should be 600
                    assert key_mode & 0o077 == 0, f"{f} is too open!"


class TestEnvironmentSecurity:
    """Environment security tests"""

    def test_path_safety(self):
        """Test PATH is safe"""
        path = os.environ.get("PATH", "")
        paths = path.split(":")

        # Should not include current directory
        assert "." not in paths, "PATH includes current directory!"
        assert "" not in paths, "PATH includes empty entry"

    def test_no_sensitive_env(self):
        """Test no sensitive environment variables"""
        sensitive_vars = [
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "DATABASE_PASSWORD",
            "API_SECRET",
        ]

        for var in sensitive_vars:
            if var in os.environ:
                print(f"WARNING: {var} is set in environment!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

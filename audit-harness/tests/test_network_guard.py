import pytest
import socket
import subprocess
import os
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field
from security.network_guard import activate_network_guard, deactivate_network_guard


@dataclass(frozen=True)
class FakeSettingsDisabled:
    ENABLE_NETWORK_GUARD: bool = False
    KILL_ON_VIOLATION: bool = False
    ALLOWED_OUTBOUND_HOSTS: list[str] = field(default_factory=lambda: ["127.0.0.1", "localhost", "::1"])


@dataclass(frozen=True)
class FakeSettingsEnabled:
    ENABLE_NETWORK_GUARD: bool = True
    KILL_ON_VIOLATION: bool = False
    ALLOWED_OUTBOUND_HOSTS: list[str] = field(default_factory=lambda: ["example.com", "127.0.0.1", "localhost", "::1"])


def test_guard_disabled_does_nothing(monkeypatch):
    monkeypatch.setattr("security.network_guard.settings", FakeSettingsDisabled(), raising=False)
    monkeypatch.setattr("config.settings.settings", FakeSettingsDisabled(), raising=False)

    original_connect = socket.socket.connect
    activate_network_guard()
    assert socket.socket.connect is original_connect
    deactivate_network_guard()


def test_guard_blocks_disallowed_host():
    from security.network_guard import _make_guarded_connect

    allowed = {"example.com", "127.0.0.1", "localhost", "::1"}
    guarded = _make_guarded_connect(allowed, kill_on_violation=False)

    with pytest.raises(ConnectionRefusedError, match="Network guard blocked"):
        guarded(socket.socket(), ("evil.com", 443))


def test_guard_allows_allowed_host():
    from security.network_guard import _make_guarded_connect

    allowed = {"example.com", "127.0.0.1", "localhost", "::1"}
    with patch.object(socket.socket, "connect") as mock_orig:
        guarded = _make_guarded_connect(allowed, kill_on_violation=False)
        guarded(socket.socket(), ("example.com", 443))
        mock_orig.assert_called_once()


def test_guard_allows_localhost():
    from security.network_guard import _make_guarded_connect

    allowed = {"example.com", "127.0.0.1", "localhost", "::1"}
    with patch.object(socket.socket, "connect") as mock_orig:
        guarded = _make_guarded_connect(allowed, kill_on_violation=False)
        guarded(socket.socket(), ("127.0.0.1", 5000))
        mock_orig.assert_called_once()


def test_guard_allows_ipv6_loopback():
    from security.network_guard import _make_guarded_connect

    allowed = {"example.com", "127.0.0.1", "localhost", "::1"}
    with patch.object(socket.socket, "connect") as mock_orig:
        guarded = _make_guarded_connect(allowed, kill_on_violation=False)
        guarded(socket.socket(), ("::1", 5000))
        mock_orig.assert_called_once()


def test_subprocess_blocked():
    from security.network_guard import _make_guarded_popen

    guarded = _make_guarded_popen({"example.com"}, kill_on_violation=False)

    with pytest.raises(PermissionError, match="Network guard blocked"):
        guarded(["echo", "hello"])


def test_os_system_blocked():
    from security.network_guard import _make_guarded_os_system

    guarded = _make_guarded_os_system(kill_on_violation=False)

    with pytest.raises(PermissionError, match="Network guard blocked"):
        guarded("echo hello")


def test_deactivation_restores_originals():
    import security.network_guard as ng
    original_connect = socket.socket.connect
    original_popen = subprocess.Popen
    original_system = os.system

    ng._original_socket_connect = original_connect
    ng._original_subprocess_popen = original_popen
    ng._original_os_system = original_system

    deactivate_network_guard()

    assert socket.socket.connect is original_connect
    assert subprocess.Popen is original_popen
    assert os.system is original_system
    assert ng._original_socket_connect is None
    assert ng._original_subprocess_popen is None
    assert ng._original_os_system is None

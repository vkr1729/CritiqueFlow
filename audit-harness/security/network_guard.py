import logging
import socket
import subprocess
import os
import sys

logger = logging.getLogger(__name__)

_original_socket_connect = None
_original_subprocess_popen = None
_original_os_system = None


def _make_guarded_connect(allowed_hosts, kill_on_violation):
    original = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in allowed_hosts:
            logger.critical("Network guard blocked connection to %s", host)
            if kill_on_violation:
                sys.exit(1)
            raise ConnectionRefusedError(f"Network guard blocked connection to {host}")
        return original(self, address)

    return guarded_connect


def _make_guarded_popen(allowed_hosts, kill_on_violation):
    original = subprocess.Popen

    def guarded_popen(*args, **kwargs):
        logger.critical("Network guard blocked subprocess.Popen call")
        if kill_on_violation:
            sys.exit(1)
        raise PermissionError("Network guard blocked subprocess.Popen call")

    return guarded_popen


def _make_guarded_os_system(kill_on_violation):
    original = os.system

    def guarded_os_system(*args, **kwargs):
        logger.critical("Network guard blocked os.system call")
        if kill_on_violation:
            sys.exit(1)
        raise PermissionError("Network guard blocked os.system call")

    return guarded_os_system


def activate_network_guard():
    global _original_socket_connect, _original_subprocess_popen, _original_os_system
    from config.settings import settings

    if not settings.ENABLE_NETWORK_GUARD:
        logger.info("Network guard disabled via ENABLE_NETWORK_GUARD=false")
        return

    allowed_hosts = set(settings.ALLOWED_OUTBOUND_HOSTS)
    kill_on_violation = settings.KILL_ON_VIOLATION

    _original_socket_connect = socket.socket.connect
    _original_subprocess_popen = subprocess.Popen
    _original_os_system = os.system

    socket.socket.connect = _make_guarded_connect(allowed_hosts, kill_on_violation)
    subprocess.Popen = _make_guarded_popen(allowed_hosts, kill_on_violation)
    os.system = _make_guarded_os_system(kill_on_violation)

    logger.info("Network guard activated — allowed: %s", sorted(allowed_hosts))


def deactivate_network_guard():
    global _original_socket_connect, _original_subprocess_popen, _original_os_system
    if _original_socket_connect is not None:
        socket.socket.connect = _original_socket_connect
    if _original_subprocess_popen is not None:
        subprocess.Popen = _original_subprocess_popen
    if _original_os_system is not None:
        os.system = _original_os_system
    _original_socket_connect = None
    _original_subprocess_popen = None
    _original_os_system = None
    logger.info("Network guard deactivated — originals restored")

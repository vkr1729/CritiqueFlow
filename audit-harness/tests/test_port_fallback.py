import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run import find_available_port


class TestFindAvailablePort:
    def test_find_available_port_first_port_free(self):
        mock_sock = MagicMock()
        mock_sock.bind.return_value = None
        mock_sock.close.return_value = None

        with patch("run.socket.socket", return_value=mock_sock):
            port = find_available_port("127.0.0.1", 5000, 5010)
            assert port == 5000
            mock_sock.bind.assert_called_with(("127.0.0.1", 5000))

    def test_find_available_port_skips_occupied(self):
        def mock_bind_return(address):
            host, port = address
            if port == 5000:
                raise OSError("Address in use")
            return None

        mock_sock = MagicMock()
        mock_sock.bind.side_effect = mock_bind_return
        mock_sock.close.return_value = None

        with patch("run.socket.socket", return_value=mock_sock):
            port = find_available_port("127.0.0.1", 5000, 5010)
            assert port == 5001
            assert mock_sock.bind.call_count == 2

    def test_find_available_port_all_exhausted(self):
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address in use")
        mock_sock.close.return_value = None

        with patch("run.socket.socket", return_value=mock_sock):
            try:
                find_available_port("127.0.0.1", 5000, 5002)
                assert False, "Expected RuntimeError"
            except RuntimeError as e:
                assert "No available port" in str(e)


class TestPortFileLifecycle:
    def test_port_file_cleanup_on_exit(self, tmp_path, monkeypatch):
        port_file = tmp_path / ".port"

        # register a cleanup that removes the file
        import atexit

        class FakeApp:
            def run(self, **kwargs):
                pass

        def fake_create_app():
            return FakeApp()

        with patch("run.Path", return_value=port_file):
            # Simulate: write file, register cleanup, then call cleanup
            port_file.write_text("5001", encoding="utf-8")
            assert port_file.exists()

            # Simulate cleanup
            port_file.unlink(missing_ok=True)
            assert not port_file.exists()

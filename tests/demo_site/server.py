"""
Minimal static file server for the demo site, with clean-URL rewriting
(/login -> login.html) so the demo site's URLs match what the fixtures'
"navigate" steps expect. No framework dependency — this only exists to
give the adapters something real to run against.
"""
from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

DEMO_SITE_DIR = Path(__file__).parent

_CLEAN_URL_MAP = {
    "/": "/index.html",
    "/login": "/login.html",
    "/contact": "/contact.html",
    "/pricing": "/pricing.html",
}


class _CleanUrlHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_SITE_DIR), **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in _CLEAN_URL_MAP:
            self.path = _CLEAN_URL_MAP[path]
        super().do_GET()

    def guess_type(self, path):
        # SimpleHTTPRequestHandler's default Content-Type omits a charset,
        # which left Chromium mis-decoding the em-dash in contact.html as
        # if it were Latin-1 despite the page's own <meta charset="utf-8">.
        # An explicit charset removes any ambiguity for the browser to sniff.
        mime = super().guess_type(path)
        if mime.startswith("text/") and "charset=" not in mime:
            return f"{mime}; charset=utf-8"
        return mime

    def log_message(self, format, *args):
        pass  # keep test output quiet


class DemoSiteServer:
    """Context manager: `with DemoSiteServer() as base_url: ...`"""

    def __init__(self, port: int = 0):
        self._httpd = socketserver.TCPServer(("127.0.0.1", port), _CleanUrlHandler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self._thread.start()
        port = self._httpd.server_address[1]
        return f"http://127.0.0.1:{port}"

    def __exit__(self, *exc_info):
        self._httpd.shutdown()
        self._httpd.server_close()

#!/usr/bin/env python3
"""Serves the interactive preview at http://localhost:8000.

The preview lives in preview/ and loads the generated PNGs straight from
docs/, so the page always shows the current renders. Only files inside the
repository are served, and the server binds to 0.0.0.0 so the Arena preview
proxy can reach it.

    python3 tools/preview_server.py             # http://localhost:8000
    python3 tools/preview_server.py --port 9000
"""
from __future__ import annotations

import argparse
import http.server
import os
import posixpath
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEW = os.path.join(ROOT, "preview")
DOCS = os.path.join(ROOT, "docs")

# Only these roots are exposed; the rest of the repository stays private.
ALLOWED_ROOTS = (PREVIEW, DOCS)

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}


class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler rooted at the repository, restricted to preview/ + docs/."""

    def translate_path(self, path: str) -> str:
        # strip query string, normalise and resolve against the repository root
        path = urllib.parse.urlsplit(path).path
        path = posixpath.normpath(urllib.parse.unquote(path))
        parts = [part for part in path.split("/") if part not in ("", ".", "..")]
        return os.path.join(ROOT, *parts)

    def _inside_allowed_roots(self, candidate: str) -> bool:
        real = os.path.realpath(candidate)
        return any(real == root or real.startswith(root + os.sep) for root in ALLOWED_ROOTS)

    def send_head(self):  # noqa: N802 - stdlib naming
        path = self.translate_path(self.path)
        if not self._inside_allowed_roots(path):
            self.send_error(404, "Not found")
            return None
        if os.path.isdir(path):
            index = os.path.join(path, "index.html")
            if not os.path.exists(index):
                self.send_error(404, "Not found")
                return None
            self.path = self.path.rstrip("/") + "/index.html"
            path = index

        if not os.path.exists(path):
            self.send_error(404, "Not found")
            return None

        try:
            handle = open(path, "rb")
        except OSError:
            self.send_error(404, "Not found")
            return None

        size = os.fstat(handle.fileno()).st_size
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(
            os.path.splitext(path)[1].lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(size))
        # the images change whenever a renderer runs: never cache them
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return handle

    def end_headers(self) -> None:
        # the Arena preview is embedded in an iframe on another origin
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Security-Policy", "frame-ancestors *")
        super().end_headers()

    def do_GET(self):  # noqa: N802 - stdlib naming
        if self.path in ("/", "/index.html"):
            self.path = "/preview/index.html"
        elif not self.path.startswith(("/preview/", "/docs/")):
            # allow short links like /docs/... and /preview/... only
            candidate = os.path.join(PREVIEW, self.path.lstrip("/"))
            if os.path.exists(candidate):
                self.path = "/preview/" + self.path.lstrip("/")
        super().do_GET()

    def log_message(self, fmt: str, *args) -> None:  # quieter output
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args(argv)

    if not os.path.exists(os.path.join(PREVIEW, "index.html")):
        raise SystemExit("preview/index.html is missing")

    with Server((args.host, args.port), PreviewHandler) as httpd:
        print(f"Pratinjau PokeLauncher: http://localhost:{args.port}/")
        print(f"  root      : {ROOT}")
        print(f"  exposing  : preview/, docs/")
        print("  Ctrl+C untuk berhenti")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nberhenti")


if __name__ == "__main__":
    main(sys.argv[1:])

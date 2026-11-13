#!/usr/bin/env python3
"""Serves the two MatePad Mini preview renders at http://localhost:8000.

Nothing else is exposed: the page shows only the device shots that
tools/render_tablet.py produces (landscape and portrait), so the preview is
exactly "the screen inside the Huawei MatePad Mini bezel".

    python3 tools/preview_server.py
    python3 tools/preview_server.py --port 9000
"""
from __future__ import annotations

import argparse
import http.server
import ipaddress
import os
import posixpath
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SHOTS = ("preview-tablet.png", "preview-tablet-portrait.png")


def render_page() -> str:
    """Builds the page from the current renders, so it cannot drift."""
    cards = []
    for name, title, note in (
        ("preview-tablet.png", "Landscape", "2560 x 1600 - layout lebar (853 dp)"),
        ("preview-tablet-portrait.png", "Portrait", "1600 x 2560 - layout ponsel (533 dp)"),
    ):
        path = os.path.join(DOCS, name)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        cards.append(f"""
      <figure class="device">
        <a href="/docs/{name}" target="_blank" rel="noopener">
          <img src="/docs/{name}" alt="PokeLauncher di dalam bezel MatePad Mini, {title.lower()}" loading="lazy">
        </a>
        <figcaption><strong>{title}</strong><span>{note}</span>
          <span class="muted">{size // 1024} KB</span></figcaption>
      </figure>""")
    return PAGE.format(cards="".join(cards))


PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokeLauncher - MatePad Mini</title>
<style>
  :root {{
    --paper: #fbf3dc; --paper-deep: #f3e4bf; --ink: #3b2f1e; --ink-soft: #6b5b44;
    --ink-faint: #9a8768; --gold: #e0b84c; --sky: #9fd4d2; --hill: #8faf74; --grass: #5f7f4c;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; padding: clamp(18px, 4vw, 44px);
    background:
      radial-gradient(900px 480px at 78% -8%, rgba(159,212,210,.62), transparent 62%),
      linear-gradient(180deg, #f4e7be 0%, var(--paper) 46%, var(--paper) 100%);
    color: var(--ink); font-family: "Trebuchet MS", "Segoe UI", system-ui, sans-serif;
  }}
  header {{ max-width: 1080px; margin: 0 auto clamp(18px, 3vw, 30px); }}
  h1 {{ margin: 0; font: 700 clamp(20px, 3vw, 27px)/1.2 "Courier New", monospace; letter-spacing: .04em; }}
  header p {{ margin: 6px 0 0; color: var(--ink-soft); font-size: 13.5px; max-width: 62ch; }}
  .badge {{
    display: inline-block; margin-bottom: 10px; padding: 5px 10px; border: 2px solid var(--ink);
    border-radius: 999px; background: var(--gold); font: 700 10.5px/1 "Courier New", monospace;
    letter-spacing: .1em; text-transform: uppercase;
  }}
  main {{
    max-width: 1080px; margin: 0 auto; display: grid; gap: clamp(18px, 3vw, 30px);
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); align-items: start;
  }}
  .device {{ margin: 0; }}
  .device a {{ display: block; }}
  .device img {{
    display: block; width: 100%; height: auto; border-radius: 12px;
    filter: drop-shadow(0 12px 26px rgba(59,47,30,.22));
    transition: transform .18s ease;
  }}
  .device a:hover img {{ transform: translateY(-2px); }}
  figcaption {{
    display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline;
    margin-top: 12px; font-size: 12.5px; color: var(--ink-soft);
  }}
  figcaption strong {{
    font: 700 11px/1 "Courier New", monospace; letter-spacing: .1em;
    text-transform: uppercase; color: var(--ink);
  }}
  figcaption span {{ font-size: 12px; }}
  .muted {{ color: var(--ink-faint); margin-left: auto; }}
  footer {{
    max-width: 1080px; margin: clamp(24px, 4vw, 40px) auto 0; padding-top: 14px;
    border-top: 2px solid var(--ink); font-size: 12px; color: var(--ink-soft);
  }}
  footer a {{ color: var(--ink); }}
  @media (prefers-reduced-motion: reduce) {{ .device a:hover img {{ transform: none; }} }}
</style>
</head>
<body>
<header>
  <span class="badge">Huawei MatePad Mini</span>
  <h1>PokeLauncher</h1>
  <p>Layar dan bezel MatePad Mini (8.8 inci, 2560 x 1600, 343 ppi, bezel ~4.4 mm,
     punch-hole kamera di dalam layar). Klik gambar untuk ukuran penuh.</p>
</header>
<main>{cards}
</main>
<footer>
  Render dibuat oleh <code>tools/render_tablet.py</code> dari palet asli
  <code>ui/theme/Theme.kt</code> &middot;
  <a href="https://github.com/retrobit-dev/pokelauncher">repositori</a>
</footer>
</body>
</html>
"""


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    """Serves the generated page plus the two PNGs, nothing else."""

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = urllib.parse.urlsplit(self.path).path

        if path in ("/", "/index.html"):
            body = render_page().encode("utf-8")
            self.respond(body, "text/html; charset=utf-8")
            return

        name = posixpath.basename(path)
        if path.startswith("/docs/") and name in SHOTS:
            file_path = os.path.join(DOCS, name)
            if os.path.exists(file_path):
                self.respond(open(file_path, "rb").read(), "image/png")
                return

        self.send_error(404, "Not found")

    def respond(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        # the Arena preview embeds this page in an iframe from another origin
        self.send_header("Content-Security-Policy", "frame-ancestors *")
        self.end_headers()
        self.wfile.write(body)

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

    missing = [n for n in SHOTS if not os.path.exists(os.path.join(DOCS, n))]
    if missing:
        raise SystemExit("render dulu: python3 tools/render_tablet.py\n  hilang: " + ", ".join(missing))

    with Server((args.host, args.port), PreviewHandler) as httpd:
        print(f"MatePad Mini preview: http://localhost:{args.port}/")
        print(f"  menyajikan: {', '.join(SHOTS)}")
        print("  Ctrl+C untuk berhenti")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nberhenti")


if __name__ == "__main__":
    main(sys.argv[1:])

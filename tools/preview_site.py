#!/usr/bin/env python3
"""Serve a fresh Pages build locally with GitHub Pages-style clean URLs."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from .build_site import build_site
except ImportError:
    from build_site import build_site


class PagesHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        translated = Path(super().translate_path(path))
        # Match GitHub Pages: /имя serves the corresponding имя.html while
        # leaving the address bar unchanged. A directory still takes priority.
        if not translated.exists():
            html_file = translated.with_name(translated.name + ".html")
            if html_file.is_file():
                return str(html_file)
        return str(translated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()

    with TemporaryDirectory(prefix="dyuym-preview-") as temp:
        build_site(temp)
        handler = partial(PagesHandler, directory=temp)
        with ThreadingHTTPServer((args.bind, args.port), handler) as server:
            print(f"Preview listening on http://{args.bind}:{args.port}/ (restart after editing)", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()

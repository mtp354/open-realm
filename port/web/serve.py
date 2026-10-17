#!/usr/bin/env python3
"""Serve the private browser build on localhost with pthread isolation headers."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class IsolatedHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT / 'build/web/engine')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not (args.directory / 'maps.html').is_file():
        parser.error('build directory has no maps.html; run make web-warcraft3-engine first')
    handler = partial(IsolatedHandler, directory=str(args.directory.resolve()))
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Open http://127.0.0.1:{args.port}/maps.html', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()

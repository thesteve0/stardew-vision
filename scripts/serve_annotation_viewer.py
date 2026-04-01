#!/usr/bin/env python3
"""
Simple HTTP server for annotation viewer.

Serves the workspace directory on port 8888 so annotation_viewer.html
can load images via relative paths.
"""

import argparse
import http.server
import os
import socketserver
import sys
from pathlib import Path


def serve_annotation_viewer(port: int = 8888, directory: Path | None = None):
    """Start HTTP server for annotation viewer."""

    if directory is None:
        # Serve from workspace root (parent of scripts/)
        directory = Path(__file__).parent.parent

    # Validate annotation viewer exists
    html_file = directory / "annotation_viewer.html"
    if not html_file.exists():
        print(f"ERROR: annotation_viewer.html not found at {html_file}")
        print("Generate it first with: python scripts/generate_annotation_viewer.py")
        sys.exit(1)

    # Change to serving directory
    os.chdir(directory)

    # Start server
    handler = http.server.SimpleHTTPRequestHandler

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"{'='*70}")
            print(f"Annotation Viewer Server Started")
            print(f"{'='*70}")
            print(f"")
            print(f"Annotation Viewer: http://localhost:{port}/annotation_viewer.html")
            print(f"")
            print(f"Serving directory: {directory}")
            print(f"")
            print(f"Instructions:")
            print(f"  1. Open http://localhost:{port}/annotation_viewer.html in your browser")
            print(f"  2. In a separate terminal, run: python scripts/interactive_annotate.py")
            print(f"  3. Follow the prompts to annotate each image")
            print(f"")
            print(f"Press Ctrl+C to stop the server")
            print(f"{'='*70}")
            print(f"")

            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nERROR: Port {port} is already in use")
            print(f"Try a different port: python {sys.argv[0]} --port {port + 1}")
        else:
            print(f"\nERROR: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="HTTP server for annotation viewer",
        epilog="Example: python scripts/serve_annotation_viewer.py --port 8888"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to serve on (default: 8888)"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=None,
        help="Directory to serve (default: workspace root)"
    )

    args = parser.parse_args()
    serve_annotation_viewer(args.port, args.directory)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for OCR service endpoint.

Sends a Pierre's shop screenshot to the OCR service and prints the response.
Useful for testing local Docker container or OpenShift deployment.
"""

import argparse
import base64
import sys
from pathlib import Path

import requests


def test_ocr_service(image_path: str, service_url: str = "http://localhost:8002", debug: bool = False):
    """Send an image to the OCR service and print the response.

    Args:
        image_path: Path to screenshot image file
        service_url: Base URL of OCR service (default: http://localhost:8002)
        debug: Whether to request debug output from OCR service
    """
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    # Read and encode image
    with open(image_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Send request
    endpoint = f"{service_url}/extract/pierres-detail-panel"
    payload = {'image_b64': img_b64, 'debug': debug}

    print(f"Sending request to {endpoint}")
    print(f"Image: {image_path.name} ({len(img_b64)} bytes base64)")

    try:
        response = requests.post(endpoint, json=payload, timeout=60)
        print(f"\nStatus: {response.status_code}")

        if response.ok:
            result = response.json()
            print("\nResponse:")
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"Error response: {response.text}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test OCR service endpoint")
    parser.add_argument("image", help="Path to screenshot image file")
    parser.add_argument(
        "--url",
        default="http://localhost:8002",
        help="OCR service base URL (default: http://localhost:8002)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Request debug output from OCR service"
    )

    args = parser.parse_args()
    test_ocr_service(args.image, args.url, args.debug)

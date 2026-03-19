import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Stardew Vision — accessibility OCR pipeline")
    parser.add_argument("--image", help="Path to a Stardew Valley screenshot to process")
    parser.add_argument("--debug", action="store_true", help="Print OCR boxes and Y positions")
    args = parser.parse_args()

    if args.image:
        from stardew_vision.tools.crop_pierres_detail_panel import crop_pierres_detail_panel

        result = crop_pierres_detail_panel(args.image, debug=args.debug)
        print(json.dumps(result, indent=2))
    else:
        print("Hello from stardew-vision!")
        print("Use --image <path> to extract fields from a Pierre's shop screenshot.")


if __name__ == "__main__":
    main()

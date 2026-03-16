#!/usr/bin/env python3
"""
Sprite Viewer - Browse Stardew Valley item sprites

This script allows you to view sprites filtered by ID, name, or type.
Supports CLI display (matplotlib) and HTML catalog generation.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
import argparse


def load_manifest(manifest_path: Path) -> Dict:
    """Load the item manifest."""
    with open(manifest_path) as f:
        return json.load(f)


def show_sprite_cli(item_id: str, manifest: Dict, assets_dir: Path):
    """Display a single sprite using matplotlib."""
    try:
        from PIL import Image
        import matplotlib.pyplot as plt
    except ImportError:
        print("Error: matplotlib and PIL required for CLI display")
        print("Install with: pip install matplotlib pillow")
        return

    if item_id not in manifest:
        print(f"Error: Item ID '{item_id}' not found")
        return

    item = manifest[item_id]
    sprite_path = assets_dir / item['sprite_file']

    if not sprite_path.exists():
        print(f"Error: Sprite file not found: {sprite_path}")
        return

    # Load and display sprite
    sprite = Image.open(sprite_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Original 16x16
    ax1.imshow(sprite)
    ax1.set_title(f"Original (16×16)\nID: {item_id}")
    ax1.axis('off')

    # Scaled 4x (64x64) for better viewing
    scaled = sprite.resize((64, 64), Image.NEAREST)
    ax2.imshow(scaled)
    ax2.set_title(f"Scaled 4× (64×64)")
    ax2.axis('off')

    # Add item info
    info = f"Name: {item['name']}\n"
    info += f"Display: {item['display_name']}\n"
    info += f"Type: {item['type']}\n"
    info += f"Price: {item['price']}g\n"
    info += f"SpriteIndex: {item['sprite_index']}"

    plt.suptitle(info, fontsize=10, ha='left', x=0.1)
    plt.tight_layout()
    plt.show()


def show_sprites_by_type_cli(item_type: str, manifest: Dict, assets_dir: Path, limit: int = 20):
    """Display sprites of a specific type in a grid."""
    try:
        from PIL import Image
        import matplotlib.pyplot as plt
    except ImportError:
        print("Error: matplotlib and PIL required for CLI display")
        print("Install with: pip install matplotlib pillow")
        return

    # Filter items by type
    items = [(iid, item) for iid, item in manifest.items()
             if item['type'].lower() == item_type.lower()]

    if not items:
        print(f"Error: No items found with type '{item_type}'")
        print(f"Available types: {sorted(set(item['type'] for item in manifest.values()))}")
        return

    print(f"Found {len(items)} items of type '{item_type}'")

    # Limit display
    if len(items) > limit:
        print(f"Showing first {limit} items (use --limit to change)")
        items = items[:limit]

    # Create grid
    cols = 5
    rows = (len(items) + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3))
    if rows == 1:
        axes = [axes]
    axes = [ax for row in axes for ax in (row if hasattr(row, '__iter__') else [row])]

    for idx, (item_id, item) in enumerate(items):
        sprite_path = assets_dir / item['sprite_file']
        if not sprite_path.exists():
            continue

        sprite = Image.open(sprite_path)
        scaled = sprite.resize((64, 64), Image.NEAREST)

        axes[idx].imshow(scaled)
        axes[idx].set_title(f"{item['name']}\nID: {item_id}", fontsize=8)
        axes[idx].axis('off')

    # Hide unused subplots
    for idx in range(len(items), len(axes)):
        axes[idx].axis('off')

    plt.suptitle(f"Type: {item_type} ({len(items)} items)", fontsize=14)
    plt.tight_layout()
    plt.show()


def search_by_name(query: str, manifest: Dict) -> List[tuple]:
    """Search items by name (case-insensitive partial match)."""
    query = query.lower()
    results = []
    for item_id, item in manifest.items():
        if (query in item['name'].lower() or
            query in item['display_name'].lower()):
            results.append((item_id, item))
    return results


def clean_display_name(display_name: str) -> str:
    """
    Extract clean name from localized text format.

    Converts "[LocalizedText Strings\\Objects:Weeds_Name]" to "Weeds_Name"
    """
    if display_name.startswith('[LocalizedText') and ':' in display_name and ']' in display_name:
        # Extract text between ":" and "]"
        start = display_name.find(':') + 1
        end = display_name.rfind(']')
        return display_name[start:end]
    return display_name


def generate_html_catalog(manifest: Dict, assets_dir: Path, output_path: Path,
                          filter_type: Optional[str] = None):
    """Generate an HTML catalog of all sprites."""
    from PIL import Image
    import base64
    from io import BytesIO

    # Filter items if type specified
    items = manifest.items()
    if filter_type:
        items = [(iid, item) for iid, item in items
                if item['type'].lower() == filter_type.lower()]
        title = f"Stardew Valley Sprites - Type: {filter_type}"
    else:
        title = "Stardew Valley Sprites Catalog"

    # Group by type
    by_type = {}
    for item_id, item in items:
        item_type = item['type']
        if item_type not in by_type:
            by_type[item_type] = []
        by_type[item_type].append((item_id, item))

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #ccc;
            padding-bottom: 5px;
        }}
        .stats {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .sprite-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .sprite-card {{
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .sprite-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        .sprite-img {{
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
            width: 64px;
            height: 64px;
            margin: 10px auto;
        }}
        .sprite-name {{
            font-weight: bold;
            color: #333;
            margin: 5px 0;
        }}
        .sprite-id {{
            color: #666;
            font-size: 0.9em;
        }}
        .sprite-price {{
            color: #f57c00;
            font-weight: bold;
            margin-top: 5px;
        }}
        .filter-buttons {{
            margin: 20px 0;
        }}
        .filter-btn {{
            padding: 8px 16px;
            margin: 5px;
            border: 1px solid #4CAF50;
            background-color: white;
            color: #4CAF50;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .filter-btn:hover {{
            background-color: #4CAF50;
            color: white;
        }}
        .search-box {{
            padding: 10px;
            width: 300px;
            border: 2px solid #4CAF50;
            border-radius: 4px;
            font-size: 14px;
        }}
    </style>
    <script>
        function searchSprites() {{
            const input = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.sprite-card');

            cards.forEach(card => {{
                const name = card.getAttribute('data-name').toLowerCase();
                const id = card.getAttribute('data-id').toLowerCase();

                if (name.includes(input) || id.includes(input)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</head>
<body>
    <h1>{title}</h1>

    <div class="stats">
        <strong>Total Items:</strong> {len(list(items))} |
        <strong>Types:</strong> {len(by_type)} |
        <strong>Source:</strong> Stardew Valley v1.6.15.24356
    </div>

    <div class="filter-buttons">
        <input type="text" id="searchInput" class="search-box"
               onkeyup="searchSprites()" placeholder="Search by name or ID...">
    </div>
"""

    # Generate sections for each type
    for item_type in sorted(by_type.keys()):
        type_items = sorted(by_type[item_type], key=lambda x: x[0])

        html += f'\n    <h2>{item_type} ({len(type_items)} items)</h2>\n'
        html += '    <div class="sprite-grid">\n'

        for item_id, item in type_items:
            sprite_path = assets_dir / item['sprite_file']

            if not sprite_path.exists():
                continue

            # Load sprite and encode to base64
            sprite = Image.open(sprite_path)
            scaled = sprite.resize((64, 64), Image.NEAREST)

            buffered = BytesIO()
            scaled.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # Clean the display name
            clean_name = clean_display_name(item['display_name'])

            html += f'''        <div class="sprite-card" data-name="{item['name']}" data-id="{item_id}">
            <img src="data:image/png;base64,{img_str}" class="sprite-img" alt="{item['name']}">
            <div class="sprite-name">{clean_name}</div>
            <div class="sprite-id">ID: {item_id}</div>
            <div class="sprite-price">{item['price']}g</div>
        </div>
'''

        html += '    </div>\n'

    html += """
</body>
</html>
"""

    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✓ HTML catalog generated: {output_path}")
    print(f"  Items: {len(list(items))}")
    print(f"  Types: {len(by_type)}")
    print(f"\nOpen in browser: file://{output_path.absolute()}")


def list_types(manifest: Dict):
    """List all available item types with counts."""
    type_counts = {}
    for item in manifest.values():
        item_type = item['type']
        type_counts[item_type] = type_counts.get(item_type, 0) + 1

    print("Available item types:\n")
    for item_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {item_type:20s} {count:4d} items")
    print(f"\nTotal: {len(type_counts)} types, {len(manifest)} items")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path('datasets/assets'),
                       help='Path to assets directory')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Show by ID
    show_parser = subparsers.add_parser('show', help='Show sprite by ID')
    show_parser.add_argument('id', help='Item ID to display')

    # Show by type
    type_parser = subparsers.add_parser('type', help='Show sprites by type')
    type_parser.add_argument('type', help='Item type (e.g., Basic, Minerals)')
    type_parser.add_argument('--limit', type=int, default=20,
                            help='Maximum number to display')

    # Search by name
    search_parser = subparsers.add_parser('search', help='Search sprites by name')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--html', action='store_true',
                              help='Generate HTML catalog of results')

    # Generate HTML catalog
    html_parser = subparsers.add_parser('html', help='Generate HTML catalog')
    html_parser.add_argument('--output', type=Path, default=Path('sprite_catalog.html'),
                            help='Output HTML file path')
    html_parser.add_argument('--type', help='Filter by type')

    # List types
    subparsers.add_parser('types', help='List all item types')

    args = parser.parse_args()

    # Load manifest
    manifest_path = args.assets / 'item_manifest.json'
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}")
        return 1

    manifest = load_manifest(manifest_path)

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == 'show':
        show_sprite_cli(args.id, manifest, args.assets)

    elif args.command == 'type':
        show_sprites_by_type_cli(args.type, manifest, args.assets, args.limit)

    elif args.command == 'search':
        results = search_by_name(args.query, manifest)

        if not results:
            print(f"No items found matching '{args.query}'")
            return 1

        print(f"Found {len(results)} items matching '{args.query}':\n")
        for item_id, item in results[:20]:
            print(f"  {item_id:6s} - {item['name']:30s} ({item['type']})")

        if len(results) > 20:
            print(f"\n... and {len(results) - 20} more")

        if args.html:
            # Create filtered manifest
            filtered = {iid: item for iid, item in results}
            output = Path(f"search_{args.query.replace(' ', '_')}.html")
            generate_html_catalog(filtered, args.assets, output)

    elif args.command == 'html':
        generate_html_catalog(manifest, args.assets, args.output, args.type)

    elif args.command == 'types':
        list_types(manifest)

    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
roblox_shirt_maker.py — Roblox R15 Shirt Template Generator
Takes existing PNG artwork and composites it onto a proper 585x559 Roblox shirt template.

Usage:
  # Single shirt with auto-detected base color
  python roblox_shirt_maker.py art.png

  # Specify base color (hex)
  python roblox_shirt_maker.py art.png --color "#1A1A2E"

  # White shirt
  python roblox_shirt_maker.py art.png --color white

  # Put design on front AND back
  python roblox_shirt_maker.py art.png --front-and-back

  # Scale the design (default 0.85 = 85% of torso_front region)
  python roblox_shirt_maker.py art.png --scale 1.0

  # Batch mode — process all PNGs in a folder
  python roblox_shirt_maker.py --batch ./art_folder/ --color black

  # AI mode — use Gemini to pick colors and describe the design
  python roblox_shirt_maker.py art.png --ai

  # Output to specific folder
  python roblox_shirt_maker.py art.png -o ./output/

Template Layout (585x559):
  ┌─────────────────────────────┐
  │  Torso area (top ~48%)      │
  │  ┌─────┬───────┬─────┬───────┐
  │  │     │ FRONT │     │ BACK  │  ← Main design regions (128x128)
  │  │     │ 231,74│     │427,74 │
  │  └─────┴───────┴─────┴───────┘
  │                               │
  │  Sleeves (bottom ~52%)       │
  │  ┌───────────┬───────────┐   │
  │  │ Right Arm │ Left Arm  │   │
  │  └───────────┴───────────┘   │
  └─────────────────────────────┘
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

# ── Template Constants (R15 Standard) ──────────────────────────────────
TEMPLATE_WIDTH = 585
TEMPLATE_HEIGHT = 559

# Region definitions matching rotemplate/constants/templates.ts
SHIRT_REGIONS = {
    # Torso
    "torso_up":    {"x": 231, "y": 8,   "w": 128, "h": 64},
    "torso_right": {"x": 165, "y": 74,  "w": 64,  "h": 128},
    "torso_front": {"x": 231, "y": 74,  "w": 128, "h": 128},  # ← MAIN DESIGN
    "torso_left":  {"x": 361, "y": 74,  "w": 64,  "h": 128},
    "torso_back":  {"x": 427, "y": 74,  "w": 128, "h": 128},  # ← BACK DESIGN
    "torso_down":  {"x": 231, "y": 204, "w": 128, "h": 64},
    # Right Arm
    "rarm_up":    {"x": 217, "y": 289, "w": 64, "h": 64},
    "rarm_left":  {"x": 19,  "y": 355, "w": 64, "h": 128},
    "rarm_back":  {"x": 85,  "y": 355, "w": 64, "h": 128},
    "rarm_right": {"x": 151, "y": 355, "w": 64, "h": 128},
    "rarm_front": {"x": 217, "y": 355, "w": 64, "h": 128},
    "rarm_down":  {"x": 217, "y": 485, "w": 64, "h": 64},
    # Left Arm
    "larm_up":    {"x": 308, "y": 289, "w": 64, "h": 64},
    "larm_front": {"x": 308, "y": 355, "w": 64, "h": 128},
    "larm_left":  {"x": 374, "y": 355, "w": 64, "h": 128},
    "larm_back":  {"x": 440, "y": 355, "w": 64, "h": 128},
    "larm_right": {"x": 506, "y": 355, "w": 64, "h": 128},
    "larm_down":  {"x": 308, "y": 485, "w": 64, "h": 64},
}

# Common shirt colors
COLOR_MAP = {
    "black": "#1A1A2E",
    "white": "#F5F5F5",
    "navy": "#16213E",
    "red": "#E94560",
    "gray": "#424242",
    "grey": "#424242",
    "darkgray": "#212121",
    "charcoal": "#2D2D2D",
    "forest": "#1B4332",
    "burgundy": "#800020",
    "royal": "#0F3460",
    "purple": "#533483",
    "orange": "#FF5722",
    "teal": "#00BCD4",
    "olive": "#556B2F",
    "cream": "#FFFDD0",
    "pink": "#FF69B4",
    "maroon": "#800000",
}

# ── Gemini Integration ─────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
GEMINI_KEY_PATH = SCRIPT_DIR.parent / "POD_Pipeline" / "gemini_agent.py"

def get_gemini_key():
    """Get Gemini API key from environment or config."""
    key = os.environ.get("GOOGLE_AI_API_KEY")
    if key:
        return key
    # Try to read from our pipeline config
    try:
        # Check for key in our standard location
        config_path = SCRIPT_DIR.parent / "credentials" / "gemini_config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f).get("api_key")
    except:
        pass
    return None

def ai_analyze_for_shirt(image_path):
    """Use Gemini to suggest shirt color and describe the design."""
    import base64
    key = get_gemini_key()
    if not key:
        key = "AIzaSyArphXiTDxrvOicMWgnjIb1xHhwk3CQkyc"

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = """Analyze this artwork for placement on a Roblox shirt template.
Return JSON only:
{
  "description": "brief description of the art",
  "suggested_shirt_color": "#hex color that would look best as the shirt base",
  "suggested_name": "short product name for Roblox catalog",
  "art_style": "style category",
  "has_transparency": true/false
}"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": img_b64}}
            ]
        }],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.3}
    }

    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        resp = json.loads(result.stdout)
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        # Extract JSON
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

# ── Image Processing ───────────────────────────────────────────────────
def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def auto_crop(img):
    """Trim transparent borders from an image."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def dominant_color(img, dark_bias=True):
    """Get the dominant/average edge color from an image for shirt base."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Sample edges
    w, h = img.size
    pixels = []
    for x in range(w):
        for y in [0, 1, h-2, h-1]:
            p = img.getpixel((x, y))
            if p[3] > 128:  # Non-transparent
                pixels.append(p[:3])
    for y in range(h):
        for x in [0, 1, w-2, w-1]:
            p = img.getpixel((x, y))
            if p[3] > 128:
                pixels.append(p[:3])

    if not pixels:
        # All transparent edges — use dark default
        return (26, 26, 46)  # #1A1A2E

    # Average
    avg_r = sum(p[0] for p in pixels) // len(pixels)
    avg_g = sum(p[1] for p in pixels) // len(pixels)
    avg_b = sum(p[2] for p in pixels) // len(pixels)

    if dark_bias:
        # Darken slightly for better contrast
        avg_r = max(0, avg_r - 30)
        avg_g = max(0, avg_g - 30)
        avg_b = max(0, avg_b - 30)

    return (avg_r, avg_g, avg_b)

def create_shirt_template(art_path, base_color=None, scale=0.85,
                          front_and_back=False, ai_mode=False,
                          output_path=None):
    """
    Create a Roblox R15 shirt template with art centered on the torso.

    Args:
        art_path: Path to PNG artwork
        base_color: Hex color or name for shirt base (None = auto-detect)
        scale: How much of the 128x128 region to fill (0.0-1.0)
        front_and_back: Put the design on both front and back
        ai_mode: Use Gemini to pick colors
        output_path: Output file path (auto-generated if None)

    Returns:
        Path to the generated template
    """
    print(f"\n🎮 Creating Roblox shirt from: {Path(art_path).name}")

    # Load and crop the artwork
    art = Image.open(art_path).convert("RGBA")
    art = auto_crop(art)
    print(f"  Art size (cropped): {art.size[0]}x{art.size[1]}")

    # AI mode — let Gemini pick the color
    ai_info = None
    if ai_mode:
        print("  🤖 Asking Gemini for shirt recommendations...")
        ai_info = ai_analyze_for_shirt(art_path)
        if ai_info:
            print(f"  📝 {ai_info.get('description', '?')}")
            print(f"  🎨 Suggested color: {ai_info.get('suggested_shirt_color', '?')}")
            print(f"  📛 Suggested name: {ai_info.get('suggested_name', '?')}")
            if not base_color:
                base_color = ai_info.get("suggested_shirt_color", "#1A1A2E")

    # Determine base color
    if base_color:
        if base_color.lower() in COLOR_MAP:
            base_color = COLOR_MAP[base_color.lower()]
        rgb = hex_to_rgb(base_color)
    else:
        rgb = dominant_color(art)
        base_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    print(f"  🎨 Base color: {base_color}")

    # Create the template canvas
    template = Image.new("RGBA", (TEMPLATE_WIDTH, TEMPLATE_HEIGHT), (*rgb, 255))

    # Only keep pixels inside the defined regions (transparent outside)
    mask = Image.new("L", (TEMPLATE_WIDTH, TEMPLATE_HEIGHT), 0)
    mask_draw = ImageDraw.Draw(mask)
    for region in SHIRT_REGIONS.values():
        mask_draw.rectangle(
            [region["x"], region["y"],
             region["x"] + region["w"] - 1, region["y"] + region["h"] - 1],
            fill=255
        )
    template.putalpha(mask)

    # Resize art to fit the torso_front region (128x128) with scale factor
    front = SHIRT_REGIONS["torso_front"]
    target_w = int(front["w"] * scale)
    target_h = int(front["h"] * scale)

    # Maintain aspect ratio
    art_w, art_h = art.size
    art_aspect = art_w / art_h
    target_aspect = target_w / target_h

    if art_aspect > target_aspect:
        # Art is wider — fit to width
        new_w = target_w
        new_h = int(new_w / art_aspect)
    else:
        # Art is taller — fit to height
        new_h = target_h
        new_w = int(new_h * art_aspect)

    art_resized = art.resize((new_w, new_h), Image.LANCZOS)

    # Center in the torso_front region
    offset_x = front["x"] + (front["w"] - new_w) // 2
    offset_y = front["y"] + (front["h"] - new_h) // 2

    # Paste with alpha compositing
    template.paste(art_resized, (offset_x, offset_y), art_resized)
    print(f"  ✓ Placed on front: {new_w}x{new_h} at ({offset_x}, {offset_y})")

    # Optionally put on back too
    if front_and_back:
        back = SHIRT_REGIONS["torso_back"]
        back_offset_x = back["x"] + (back["w"] - new_w) // 2
        back_offset_y = back["y"] + (back["h"] - new_h) // 2
        template.paste(art_resized, (back_offset_x, back_offset_y), art_resized)
        print(f"  ✓ Placed on back: {new_w}x{new_h} at ({back_offset_x}, {back_offset_y})")

    # Generate output path
    if not output_path:
        stem = Path(art_path).stem
        output_dir = Path(art_path).parent
        output_path = output_dir / f"{stem}_roblox_shirt.png"

    template.save(str(output_path), "PNG")
    print(f"  💾 Saved: {output_path}")
    print(f"  📐 Template: {TEMPLATE_WIDTH}x{TEMPLATE_HEIGHT} (R15 standard)")

    return str(output_path), ai_info

def batch_generate(folder, base_color=None, scale=0.85,
                   front_and_back=False, ai_mode=False, output_dir=None):
    """Process all PNGs in a folder."""
    folder = Path(folder)
    pngs = sorted(folder.glob("*.png"))

    if not pngs:
        print(f"  ✗ No PNG files found in {folder}")
        return []

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    print(f"\n🎮 BATCH MODE: {len(pngs)} designs → Roblox shirts")
    print("=" * 50)

    for png in pngs:
        # Skip files that are already roblox templates
        if "_roblox_shirt" in png.stem:
            continue

        out_path = None
        if output_dir:
            out_path = output_dir / f"{png.stem}_roblox_shirt.png"

        try:
            path, info = create_shirt_template(
                str(png), base_color, scale, front_and_back, ai_mode, out_path
            )
            results.append({"source": str(png), "output": path, "ai_info": info})
        except Exception as e:
            print(f"  ✗ Failed: {png.name} — {e}")
            results.append({"source": str(png), "error": str(e)})

    # Summary
    success = sum(1 for r in results if "output" in r)
    print(f"\n{'=' * 50}")
    print(f"  ✅ {success}/{len(results)} shirts generated")

    return results

# ── CLI ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate Roblox R15 shirt templates from PNG artwork")
    parser.add_argument("input", nargs="?", help="PNG file or folder (with --batch)")
    parser.add_argument("--batch", action="store_true", help="Process all PNGs in folder")
    parser.add_argument("--color", "-c", help="Base shirt color (hex or name)")
    parser.add_argument("--scale", "-s", type=float, default=0.85, help="Design scale (0.0-1.0)")
    parser.add_argument("--front-and-back", "-fb", action="store_true", help="Place design on front AND back")
    parser.add_argument("--ai", action="store_true", help="Use Gemini AI to pick colors")
    parser.add_argument("-o", "--output", help="Output path (file or folder for batch)")
    parser.add_argument("--list-colors", action="store_true", help="Show available color names")

    args = parser.parse_args()

    if args.list_colors:
        print("\n🎨 Available color names:")
        for name, hex_val in sorted(COLOR_MAP.items()):
            print(f"  {name:<12} {hex_val}")
        return

    if not args.input:
        parser.print_help()
        return

    if args.batch or os.path.isdir(args.input):
        batch_generate(args.input, args.color, args.scale,
                       args.front_and_back, args.ai, args.output)
    else:
        create_shirt_template(args.input, args.color, args.scale,
                              args.front_and_back, args.ai, args.output)

if __name__ == "__main__":
    main()

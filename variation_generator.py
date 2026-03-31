#!/usr/bin/env python3
"""
variation_generator.py — Create wild Roblox shirt variations
Spreads backgrounds across the full template, layers art in creative patterns.
"""

import sys, os, random, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

# R15 template constants
TW, TH = 585, 559

SHIRT_REGIONS = {
    "torso_up":    (231, 8,   128, 64),
    "torso_right": (165, 74,  64,  128),
    "torso_front": (231, 74,  128, 128),
    "torso_left":  (361, 74,  64,  128),
    "torso_back":  (427, 74,  128, 128),
    "torso_down":  (231, 204, 128, 64),
    "rarm_up":     (217, 289, 64,  64),
    "rarm_left":   (19,  355, 64,  128),
    "rarm_back":   (85,  355, 64,  128),
    "rarm_right":  (151, 355, 64,  128),
    "rarm_front":  (217, 355, 64,  128),
    "rarm_down":   (217, 485, 64,  64),
    "larm_up":     (308, 289, 64,  64),
    "larm_front":  (308, 355, 64,  128),
    "larm_left":   (374, 355, 64,  128),
    "larm_back":   (440, 355, 64,  128),
    "larm_right":  (506, 355, 64,  128),
    "larm_down":   (308, 485, 64,  64),
}

def make_region_mask():
    """Create alpha mask that only shows defined regions."""
    mask = Image.new("L", (TW, TH), 0)
    draw = ImageDraw.Draw(mask)
    for (x, y, w, h) in SHIRT_REGIONS.values():
        draw.rectangle([x, y, x+w-1, y+h-1], fill=255)
    return mask

def auto_crop(img):
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img

def fit_art(art, target_w, target_h):
    """Resize art to fit within target dimensions, maintaining aspect ratio."""
    art_w, art_h = art.size
    ratio = min(target_w / art_w, target_h / art_h)
    new_w = max(1, int(art_w * ratio))
    new_h = max(1, int(art_h * ratio))
    return art.resize((new_w, new_h), Image.LANCZOS)

def spread_background(bg_path):
    """Resize background to fill the entire 585x559 template."""
    bg = Image.open(bg_path).convert("RGBA")
    return bg.resize((TW, TH), Image.LANCZOS)

def place_art_centered(canvas, art, region_name):
    """Place art centered in a specific region."""
    x, y, w, h = SHIRT_REGIONS[region_name]
    fitted = fit_art(art, int(w * 0.9), int(h * 0.9))
    ox = x + (w - fitted.size[0]) // 2
    oy = y + (h - fitted.size[1]) // 2
    canvas.paste(fitted, (ox, oy), fitted)

def place_art_tiled(canvas, art, regions, tile_scale=0.45):
    """Tile small copies of art across multiple regions."""
    for rname in regions:
        x, y, w, h = SHIRT_REGIONS[rname]
        small = fit_art(art, int(w * tile_scale), int(h * tile_scale))
        sw, sh = small.size
        for tx in range(x, x + w, sw + 2):
            for ty in range(y, y + h, sh + 2):
                if tx + sw <= x + w and ty + sh <= y + h:
                    canvas.paste(small, (tx, ty), small)

def place_art_scattered(canvas, art, regions, count=3, scale_range=(0.3, 0.6)):
    """Randomly scatter art across regions with rotation."""
    for rname in regions:
        x, y, w, h = SHIRT_REGIONS[rname]
        for _ in range(count):
            s = random.uniform(*scale_range)
            piece = fit_art(art, int(w * s), int(h * s))
            angle = random.choice([0, 15, -15, 30, -30, 45, -45])
            if angle != 0:
                piece = piece.rotate(angle, expand=True, resample=Image.BICUBIC)
            pw, ph = piece.size
            px = x + random.randint(0, max(0, w - pw))
            py = y + random.randint(0, max(0, h - ph))
            canvas.paste(piece, (px, py), piece)

def place_art_big_front(canvas, art, scale=0.85, also_back=False):
    """Classic centered front placement, optionally back too."""
    for rname in (["torso_front"] + (["torso_back"] if also_back else [])):
        x, y, w, h = SHIRT_REGIONS[rname]
        fitted = fit_art(art, int(w * scale), int(h * scale))
        ox = x + (w - fitted.size[0]) // 2
        oy = y + (h - fitted.size[1]) // 2
        canvas.paste(fitted, (ox, oy), fitted)

def apply_region_mask(canvas):
    """Apply region mask so only valid regions are visible."""
    mask = make_region_mask()
    result = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    result.paste(canvas, (0, 0), mask)
    return result

# ── Variation Styles ───────────────────────────────────────────────────

def style_bg_front(bg_path, art_path, name):
    """Background spread + big art on front chest."""
    canvas = spread_background(bg_path)
    art = auto_crop(Image.open(art_path).convert("RGBA"))
    place_art_big_front(canvas, art, 0.85, also_back=False)
    return apply_region_mask(canvas), name

def style_bg_front_back(bg_path, art_path, name):
    """Background spread + art on front AND back."""
    canvas = spread_background(bg_path)
    art = auto_crop(Image.open(art_path).convert("RGBA"))
    place_art_big_front(canvas, art, 0.85, also_back=True)
    return apply_region_mask(canvas), name

def style_bg_allover(bg_path, art_path, name):
    """Background + art tiled across ALL regions (allover print)."""
    canvas = spread_background(bg_path)
    art = auto_crop(Image.open(art_path).convert("RGBA"))
    all_regions = list(SHIRT_REGIONS.keys())
    place_art_tiled(canvas, art, all_regions, tile_scale=0.4)
    return apply_region_mask(canvas), name

def style_bg_scattered(bg_path, art_path, name):
    """Background + art scattered randomly across torso and sleeves."""
    canvas = spread_background(bg_path)
    art = auto_crop(Image.open(art_path).convert("RGBA"))
    torso = ["torso_front", "torso_back", "torso_left", "torso_right"]
    arms = ["rarm_front", "rarm_back", "larm_front", "larm_back"]
    place_art_scattered(canvas, art, torso, count=2, scale_range=(0.35, 0.55))
    place_art_scattered(canvas, art, arms, count=1, scale_range=(0.25, 0.4))
    return apply_region_mask(canvas), name

def style_bg_sleeves_art(bg_path, art_path, name):
    """Background on sleeves, solid dark torso with centered art."""
    canvas = spread_background(bg_path)
    # Dark overlay on torso regions
    draw = ImageDraw.Draw(canvas)
    for rname in ["torso_up", "torso_right", "torso_front", "torso_left",
                   "torso_back", "torso_down"]:
        x, y, w, h = SHIRT_REGIONS[rname]
        draw.rectangle([x, y, x+w-1, y+h-1], fill=(20, 20, 35, 255))
    art = auto_crop(Image.open(art_path).convert("RGBA"))
    place_art_big_front(canvas, art, 0.85, also_back=True)
    return apply_region_mask(canvas), name

def style_mirror_front_back(bg_path, art_path, name):
    """Background + front normal, back flipped (mirror effect)."""
    canvas = spread_background(bg_path)
    art = auto_crop(Image.open(art_path).convert("RGBA"))
    place_art_big_front(canvas, art, 0.85)
    # Mirror on back
    flipped = art.transpose(Image.FLIP_LEFT_RIGHT)
    x, y, w, h = SHIRT_REGIONS["torso_back"]
    fitted = fit_art(flipped, int(w * 0.85), int(h * 0.85))
    ox = x + (w - fitted.size[0]) // 2
    oy = y + (h - fitted.size[1]) // 2
    canvas.paste(fitted, (ox, oy), fitted)
    return apply_region_mask(canvas), name


# ── Main Generator ─────────────────────────────────────────────────────

STYLES = [
    ("front", style_bg_front),
    ("fb", style_bg_front_back),
    ("allover", style_bg_allover),
    ("scatter", style_bg_scattered),
    ("sleeve_pop", style_bg_sleeves_art),
    ("mirror", style_mirror_front_back),
]

def generate_variations(backgrounds, artworks, output_dir, count=25):
    """Generate creative shirt variations by mixing backgrounds + art + styles."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combos = []
    for bg in backgrounds:
        bg_name = Path(bg).stem
        for art in artworks:
            art_name = Path(art).stem
            for style_name, style_fn in STYLES:
                combos.append((bg, art, bg_name, art_name, style_name, style_fn))

    random.shuffle(combos)

    results = []
    generated = 0

    print(f"\n🎨 VARIATION GENERATOR")
    print(f"  {len(backgrounds)} backgrounds × {len(artworks)} artworks × {len(STYLES)} styles = {len(combos)} possible")
    print(f"  Generating {count} variations...")
    print("=" * 50)

    for bg, art, bg_name, art_name, style_name, style_fn in combos:
        if generated >= count:
            break

        filename = f"{art_name}_{bg_name}_{style_name}_roblox.png"
        out_path = output_dir / filename

        try:
            full_name = f"{art_name} × {bg_name} [{style_name}]"
            result, _ = style_fn(bg, art, full_name)
            result.save(str(out_path), "PNG")
            results.append({
                "file": str(out_path),
                "filename": filename,
                "art": art_name,
                "bg": bg_name,
                "style": style_name,
            })
            generated += 1
            print(f"  ✓ [{generated}/{count}] {filename}")
        except Exception as e:
            print(f"  ✗ {filename}: {e}")

    print(f"\n{'=' * 50}")
    print(f"  ✅ {generated} variations generated in {output_dir}")
    return results


if __name__ == "__main__":
    BG_DIR = Path("/sessions/gifted-brave-mendel/mnt/Documents/626Labs/POD_Pipeline/backgrounds")
    ART_DIR = Path("/sessions/gifted-brave-mendel/mnt/Documents/626Labs/POD_Pipeline/cutouts")
    FAMILY_DIR = Path("/sessions/gifted-brave-mendel/mnt/Documents/626Labs/POD_Pipeline/clean_original_art")
    OUT_DIR = Path("/sessions/gifted-brave-mendel/mnt/Documents/626Labs/roblox/variations")

    backgrounds = sorted(BG_DIR.glob("*.png"))

    # Cutouts + select clean family art
    artworks = sorted(ART_DIR.glob("*.png"))
    family_clean = [
        FAMILY_DIR / "carter_abstract_man_clean.png",
        FAMILY_DIR / "elliott_spider_clean.png",
        FAMILY_DIR / "este_daisy_clean.png",
        FAMILY_DIR / "sabrina_flowers_clean.png",
        FAMILY_DIR / "sunny_crab_clean.png",
    ]
    artworks.extend([f for f in family_clean if f.exists()])

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    results = generate_variations(
        [str(b) for b in backgrounds],
        [str(a) for a in artworks],
        str(OUT_DIR),
        count=count
    )

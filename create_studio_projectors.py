"""
create_studio_projectors.py
Generates 18 ultra-clean, studio-quality 3D-style projector product images.
Rendered on a pure white background with realistic metallic/matte chassis,
antireflective multi-coated optical glass lenses, ventilation grilles, and soft contact shadows.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

IMAGE_DIR = r"D:\3rd year\2nd sem\DA2\Ecommerce\static\images\products"
os.makedirs(IMAGE_DIR, exist_ok=True)

PROJECTORS = [
    ("epson_hc2350.jpg", "Epson Home Cinema 2350", "EPSON", "#f8fafc", "#e2e8f0", "#38bdf8", "3LCD 4K"),
    ("benq_ht3550i.jpg", "BenQ HT3550i", "BenQ", "#334155", "#1e293b", "#06b6d4", "HDR PRO 4K"),
    ("sony_vpl.jpg", "Sony VPL-VW325ES", "SONY", "#0f172a", "#020617", "#60a5fa", "SXRD 4K Native"),
    ("nebula_capsule.jpg", "Anker Nebula Capsule 3", "ANKER", "#18181b", "#27272a", "#f43f5e", "Laser 1080P"),
    ("optoma_ml1080.jpg", "Optoma ML1080ST", "Optoma", "#f1f5f9", "#cbd5e1", "#10b981", "RGB Triple Laser"),
    ("epson_ebw52.jpg", "Epson EB-W52", "EPSON", "#ffffff", "#e2e8f0", "#3b82f6", "3LCD Business"),
    ("lg_cinebeam.jpg", "LG CineBeam HU85LA", "LG", "#f8fafc", "#e2e8f0", "#8b5cf6", "Triple Laser UST"),
    ("benq_w4000i.jpg", "BenQ W4000i", "BenQ", "#1e293b", "#0f172a", "#06b6d4", "4LED Cinematic"),
    ("optoma_uhd50x.jpg", "Optoma UHD50X", "Optoma", "#ffffff", "#f1f5f9", "#3b82f6", "240Hz 4K Gaming"),
    ("samsung_lsp9t.jpg", "Samsung The Premiere LSP9T", "SAMSUNG", "#f8fafc", "#e2e8f0", "#6366f1", "Triple Laser 4K"),
    ("epson_ls500.jpg", "Epson LS500", "EPSON", "#0f172a", "#1e293b", "#0ea5e9", "Ultra Short Throw"),
    ("hisense_px1.jpg", "Hisense PX1-PRO", "Hisense", "#334155", "#1e293b", "#14b8a6", "TriChroma Laser"),
    ("barco_dp2k.jpg", "Barco DP2K-10S", "BARCO", "#1e293b", "#0f172a", "#f59e0b", "2K DCI Cinema"),
    ("optoma_zh606.jpg", "Optoma ZH606", "Optoma", "#ffffff", "#e2e8f0", "#10b981", "DuraCore Laser"),
    ("christie_hd20k.jpg", "Christie Roadster HD20K-J", "CHRISTIE", "#0f172a", "#020617", "#f97316", "20,000 Lumens"),
    ("epson_ls12000b.jpg", "Epson EH-LS12000B", "EPSON", "#09090b", "#18181b", "#38bdf8", "Pro Cinema Laser"),
    ("viewsonic_x100.jpg", "ViewSonic X100-4K+", "ViewSonic", "#1e293b", "#334155", "#10b981", "LED 4K Smart"),
    ("xgimi_horizon.jpg", "XGIMI Horizon Ultra", "XGIMI", "#d6d3d1", "#a8a29e", "#eab308", "Dual Light 4K"),
]

def render_projector(filename, name, brand, body_color, secondary_color, lens_glow, badge_text):
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color="#ffffff")
    draw = ImageDraw.Draw(img)

    # 1. Soft Floor Contact Shadow
    shadow = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([140, 450, 660, 520], fill=(15, 23, 42, 60))
    sdraw.ellipse([200, 465, 600, 505], fill=(15, 23, 42, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img.paste(shadow, (0, 0), shadow)
    draw = ImageDraw.Draw(img)

    # 2. Main Projector Chassis / Body
    bx0, by0, bx1, by1 = 180, 200, 620, 460
    
    # Stand / Base
    draw.rounded_rectangle([220, 440, 580, 480], radius=12, fill=secondary_color, outline="#94a3b8", width=2)

    # Main Body
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=24, fill=body_color, outline="#cbd5e1", width=3)

    # Chassis Accent Top Bar
    draw.rounded_rectangle([bx0 + 20, by0 + 15, bx1 - 20, by0 + 55], radius=8, fill=secondary_color)

    # Front Ventilation Slits / Grille
    for y in range(by0 + 100, by1 - 40, 14):
        draw.line([bx0 + 35, y, bx0 + 130, y], fill="#94a3b8", width=4)

    # 3. Optical Glass Cinema Lens (Circular multi-ring housing)
    lx, ly, lr = 460, 330, 95
    
    # Outer Metallic Bezel
    draw.ellipse([lx - lr - 12, ly - lr - 12, lx + lr + 12, ly + lr + 12], fill="#1e293b", outline="#64748b", width=3)
    draw.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill="#0f172a")

    # Lens Glass Coating Gradient Rings
    draw.ellipse([lx - lr + 15, ly - lr + 15, lx + lr - 15, ly + lr - 15], fill=secondary_color)
    draw.ellipse([lx - lr + 30, ly - lr + 30, lx + lr - 30, ly + lr - 30], fill="#09090b")
    draw.ellipse([lx - lr + 45, ly - lr + 45, lx + lr - 45, ly + lr - 45], fill=lens_glow)
    
    # Core Aperture Reflection
    draw.ellipse([lx - 25, ly - 25, lx + 25, ly + 25], fill="#020617")
    draw.ellipse([lx - 12, ly - 22, lx + 8, ly - 6], fill="#ffffff") # White Glass Glint

    # 4. Power & Status LEDs
    draw.ellipse([bx0 + 40, by0 + 30, bx0 + 52, by0 + 42], fill="#22c55e")
    draw.ellipse([bx0 + 62, by0 + 30, bx0 + 74, by0 + 42], fill="#38bdf8")

    # 5. Brand Logo & Spec Text on Chassis
    try:
        font_brand = ImageFont.truetype("arialbd.ttf", 26)
        font_badge = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_brand = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    text_color = "#0f172a" if body_color in ["#ffffff", "#f8fafc", "#f1f5f9", "#d6d3d1"] else "#f8fafc"
    draw.text((bx0 + 95, by0 + 22), brand, fill=text_color, font=font_brand)
    draw.text((bx0 + 35, by1 - 32), badge_text, fill="#64748b", font=font_badge)

    # Save high quality JPEG
    dest = os.path.join(IMAGE_DIR, filename)
    img.save(dest, "JPEG", quality=95)
    print(f"  [RENDERED] {filename}")

def main():
    print("=== Generating 18 Studio Projector Hardware Renders ===")
    for p in PROJECTORS:
        render_projector(*p)
    print("=== All 18 Studio Projectors Generated Successfully ===")

if __name__ == "__main__":
    main()

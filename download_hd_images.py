"""
download_hd_images.py
Downloads high-resolution, clean studio product photos for all 18 projectors.
All images are selected to be clean, sharp projector hardware photos on neutral/white studio backgrounds.
"""
import os
import urllib.request

IMAGE_DIR = r"D:\3rd year\2nd sem\DA2\Ecommerce\static\images\products"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Curated high quality direct URLs of clean studio projector images
URL_MAP = {
    "epson_hc2350.jpg": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&q=85&auto=format&fit=crop",
    "benq_ht3550i.jpg": "https://images.unsplash.com/photo-1595935736128-db1f0a261263?w=800&q=85&auto=format&fit=crop",
    "sony_vpl.jpg": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=85&auto=format&fit=crop",
    "nebula_capsule.jpg": "https://images.unsplash.com/photo-1584905066893-7d5c142ba4e1?w=800&q=85&auto=format&fit=crop",
    "optoma_ml1080.jpg": "https://images.unsplash.com/photo-1600132806370-bf17e65e942f?w=800&q=85&auto=format&fit=crop",
    "epson_ebw52.jpg": "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=800&q=85&auto=format&fit=crop",
    "lg_cinebeam.jpg": "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=800&q=85&auto=format&fit=crop",
    "benq_w4000i.jpg": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=800&q=85&auto=format&fit=crop",
    "optoma_uhd50x.jpg": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=85&auto=format&fit=crop",
    "samsung_lsp9t.jpg": "https://images.unsplash.com/photo-1507646227500-4d389b0012be?w=800&q=85&auto=format&fit=crop",
    "epson_ls500.jpg": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&q=85&auto=format&fit=crop",
    "hisense_px1.jpg": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&q=85&auto=format&fit=crop",
    "barco_dp2k.jpg": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=85&auto=format&fit=crop",
    "optoma_zh606.jpg": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&q=85&auto=format&fit=crop",
    "christie_hd20k.jpg": "https://images.unsplash.com/photo-1563089145-599997674d42?w=800&q=85&auto=format&fit=crop",
    "epson_ls12000b.jpg": "https://images.unsplash.com/photo-1461151304267-38535e780c79?w=800&q=85&auto=format&fit=crop",
    "viewsonic_x100.jpg": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=800&q=85&auto=format&fit=crop",
    "xgimi_horizon.jpg": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=800&q=85&auto=format&fit=crop",
}

def main():
    print("=== Downloading Clean Studio Images ===")
    headers = {"User-Agent": "Mozilla/5.0"}
    for filename, url in URL_MAP.items():
        dest = os.path.join(IMAGE_DIR, filename)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            print(f"  [OK] {filename} ({os.path.getsize(dest)//1024} KB)")
        except Exception as e:
            print(f"  [ERR] {filename}: {e}")
    print("=== Done ===")

if __name__ == "__main__":
    main()

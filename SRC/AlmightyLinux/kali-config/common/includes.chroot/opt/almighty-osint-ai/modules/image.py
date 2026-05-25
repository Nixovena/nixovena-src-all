import os
import urllib.parse
from core import C, box, prompt, ok, warn, err, info, row


def extract_exif(path):
    try:
        from PIL import Image, ExifTags
    except Exception:
        return None, "Pillow not installed"
    try:
        img = Image.open(path)
        raw = img.getexif()
        if not raw:
            return {}, None
        out = {}
        for tag_id, value in raw.items():
            tag = ExifTags.TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = str(value)
            out[tag] = str(value)[:300]
        return out, None
    except Exception as e:
        return None, str(e)


def perceptual_hash(path):
    try:
        from PIL import Image
        import imagehash
    except Exception:
        return None
    try:
        img = Image.open(path)
        return {
            "phash": str(imagehash.phash(img)),
            "dhash": str(imagehash.dhash(img)),
            "ahash": str(imagehash.average_hash(img)),
            "whash": str(imagehash.whash(img)),
        }
    except Exception:
        return None


def reverse_search_urls(filename):
    name = urllib.parse.quote(os.path.basename(filename))
    return {
        "Google Images":  f"https://www.google.com/searchbyimage?image_url={name}",
        "Yandex Images":  f"https://yandex.com/images/search?rpt=imageview&url={name}",
        "TinEye":         "https://tineye.com/  (drag & drop)",
        "Bing Visual":    "https://www.bing.com/visualsearch  (paste image)",
    }


def dispatch(ctx, target, render_out=True):
    p = (target or "").strip()
    if not p or not os.path.isfile(p):
        if render_out: err("File does not exist")
        return None, "no file"
    exif, perr = extract_exif(p)
    h = perceptual_hash(p)
    rev = reverse_search_urls(p)
    data = {"path": p, "size": os.path.getsize(p),
            "exif": exif or {}, "exif_error": perr, "hashes": h or {}, "reverse_urls": rev}
    summary = f"Image {os.path.basename(p)}: EXIF tags={len(exif or {})}"
    if render_out:
        if perr:
            warn(perr)
        elif exif:
            ok(f"EXIF tags: {len(exif)}")
            keys = ["Make","Model","Software","DateTime","DateTimeOriginal","GPSInfo",
                    "LensModel","ExposureTime","FNumber","ISOSpeedRatings","FocalLength",
                    "Artist","Copyright"]
            for k in keys:
                if k in exif:
                    row(k, exif[k])
            if "GPSInfo" in exif:
                warn("Location data present in image!")
        else:
            info("No EXIF metadata (likely sanitized)")
        if h:
            for k, v in h.items():
                row(k, v)
        else:
            warn("imagehash/PIL not installed; skipping perceptual hashes")
        info("Reverse-image search shortcuts:")
        for name, url in rev.items():
            print(f"    {C.CYAN}- {name:<16}{C.RESET} {C.DIM}{url}{C.RESET}")
    ctx.session.add_finding("image", p, data, summary=summary)
    return data, summary


def run(ctx):
    box("Image Forensics", C.BR_GRN)
    p = prompt("Path to image file")
    dispatch(ctx, p)

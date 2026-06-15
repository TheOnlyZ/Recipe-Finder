import ssl
import time
import urllib.request
from pathlib import Path

import certifi

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())


def download_text(book_id: int, url: str, cache_dir: Path, delay: float = 0.5) -> Path | None:
    dest = cache_dir / f"pg{book_id}.txt"
    if dest.exists():
        return dest
    print(f"Downloading book {book_id}...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=_ssl_ctx) as resp:
            with open(dest, "wb") as f:
                f.write(resp.read())
    except Exception as e:
        print(f"  Failed to download book {book_id}: {e}")
        return None
    time.sleep(delay)
    return dest

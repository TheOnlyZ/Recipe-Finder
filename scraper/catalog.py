import csv
import re
import ssl
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field

import certifi

CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())
COOKBOOK_SUBJECT_PATTERN = re.compile(
    r"(cook(ery|book|ing|s)?|recipe|baking|food|culinary|kitchen|diet)", re.IGNORECASE
)


@dataclass
class BookEntry:
    id: int
    title: str
    authors: str
    subjects: str
    text_url: str


def download_catalog(catalog_path: Path) -> Path:
    if catalog_path.exists():
        return catalog_path
    print(f"Downloading catalog from {CATALOG_URL}...")
    req = urllib.request.Request(CATALOG_URL)
    with urllib.request.urlopen(req, context=_ssl_ctx) as resp:
        with open(catalog_path, "wb") as f:
            f.write(resp.read())
    print(f"Saved to {catalog_path}")
    return catalog_path


def is_cookbook(subjects: str) -> bool:
    if not subjects:
        return False
    parts = subjects.lower().split(";")
    subj = [p.strip() for p in parts]
    s_combined = " ".join(subj)
    s_clean = re.sub(r"[^a-z0-9\s]", " ", s_combined)
    s_clean = re.sub(r"\s+", " ", s_clean)

    include_any = re.compile(
        r"\b(cook(ery|book|ing)?|baking|confectionery|"
        r"pastry|culinary|cookbooks|cookery)\b", re.IGNORECASE
    )

    exclude_any = re.compile(
        r"\b(science|methodology|fiction|juvenile|"
        r"hygiene|therapeutics|fantasy|poetry|drama|"
        r"biography|history|philosophy|religion|"
        r"political|nursing|medicine|physics|chemistry|"
        r"engineering|mathematics|education|psychology)\b", re.IGNORECASE
    )

    if not include_any.search(s_clean):
        return False
    if exclude_any.search(s_clean):
        return False
    return True


def filter_cookbooks(catalog_path: Path, max_books: int = 30) -> list[BookEntry]:
    entries: list[BookEntry] = []
    with open(catalog_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            subjects = (row.get("Subjects") or "").strip()
            if not is_cookbook(subjects):
                continue
            book_id = row.get("Text#", "").strip()
            if not book_id or not book_id.isdigit():
                continue
            entries.append(
                BookEntry(
                    id=int(book_id),
                    title=(row.get("Title") or "").strip(),
                    authors=(row.get("Authors") or "").strip(),
                    subjects=subjects,
                    text_url=f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
                )
            )
            if len(entries) >= max_books:
                break
    print(f"Found {len(entries)} cookbook entries")
    return entries

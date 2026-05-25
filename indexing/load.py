import os
import re
from datetime import datetime
from langchain_core.documents import Document

TECHNICAL_FOLDERS = ["cloud", "dsa", "webd", "projects", "rags"]

def normalize_date(date_str):
    """Always store dates as DD/MM/YYYY regardless of input format."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return date_str

def extract_headings(content):
    """Extract all headings (h1, h2, h3) from markdown."""
    headings = re.findall(r'^#{1,3}\s+(.+)', content, re.MULTILINE)
    return [h.strip() for h in headings]

def extract_all_dates(content):
    """Extract all dates from file, normalized to DD/MM/YYYY."""
    raw_dates = re.findall(r'\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})\b', content)
    seen = set()
    normalized = []
    for d in raw_dates:
        n = normalize_date(d)
        if n not in seen:
            seen.add(n)
            normalized.append(n)
    return normalized

def load_file(filepath):
    if not filepath.endswith(".md"):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.strip():
        return None

    filename = os.path.basename(filepath).replace(".md", "")
    note_type = "technical" if any(f in filepath for f in TECHNICAL_FOLDERS) else "personal"

    # extract all headings
    headings = extract_headings(content)
    primary_title = headings[0] if headings else filename

    # extract all dates normalized
    all_dates = extract_all_dates(content)
    primary_date = all_dates[0] if all_dates else "unknown"

    metadata = {
        "source": filepath,
        "filename": filename,                        # e.g. "poems"
        "title": primary_title,                      # first heading
        "headings": ", ".join(headings),             # all headings as searchable string
        "date": primary_date,                        # first date (for single-date notes)
        "all_dates": ", ".join(all_dates),           # all dates (for multi-poem files)
        "type": note_type,
    }

    return [Document(page_content=content, metadata=metadata)]
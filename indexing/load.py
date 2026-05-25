import os
import re
from langchain_core.documents import Document

TECHNICAL_FOLDERS = ["cloud", "dsa", "webd"]

def load_file(filepath):
    if not filepath.endswith(".md"):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.strip():
        return None

    title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else os.path.basename(filepath).replace(".md", "")

    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b', content)
    date = date_match.group(1) if date_match else None

    # tag as technical or personal based on folder
    note_type = "technical" if any(f in filepath for f in TECHNICAL_FOLDERS) else "personal"

    metadata = {
        "source": filepath,
        "title": title,
        "date": date if date else "unknown",
        "filename": os.path.basename(filepath),
        "type": note_type        # clean tag we can filter on reliably
    }

    return [Document(page_content=content, metadata=metadata)]
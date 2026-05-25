import re
from datetime import datetime

TECHNICAL_FOLDERS = ["cloud", "dsa", "webd", "projects", "rags"]

PERSONAL_KEYWORDS = [
    "poem", "letter", "diary", "journal", "wrote", "writing",
    "feel", "feeling", "felt", "emotion", "personal", "art",
    "dream", "memory", "memories", "thought", "story", "unsent",
    "issue", "issues", "problem", "struggle", "conflict",
    "worried", "worry", "anxiety", "sad", "happy", "angry",
    "frustrated", "confused", "lost", "stuck", "my", "i am",
    "im", "i've", "ive", "i feel", "i think", "i want", "i need"
]

TECHNICAL_KEYWORDS = [
    "code", "function", "array", "algorithm", "database", "server",
    "cloud", "aws", "docker", "html", "css", "javascript", "python",
    "dsa", "web", "api", "bug", "error", "class", "loop"
]

def normalize_date(date_str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return date_str

def retrieve(vectorstore, query):
    query_lower = query.lower()

    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b', query)
    is_personal = any(word in query_lower for word in PERSONAL_KEYWORDS)
    is_technical = any(word in query_lower for word in TECHNICAL_KEYWORDS)

    # check if query mentions a filename directly e.g. "poems" "daily notes" "journal"
    # we do a broad similarity search but boost with filename filter
    filename_search = re.search(r'(?:in|from|file|note|called|named)\s+["\']?(\w[\w\s]*?)["\']?(?:\s|$)', query_lower)
    mentioned_filename = filename_search.group(1).strip() if filename_search else None

    if date_match:
        normalized = normalize_date(date_match.group(1))
        search_kwargs = {
            "k": 6,
            "filter": {"all_dates": {"$contains": normalized}}
        }
        search_type = "similarity"

    elif mentioned_filename:
        # user mentioned a specific file — filter by filename
        search_kwargs = {
            "k": 6,
            "filter": {"filename": {"$contains": mentioned_filename}}
        }
        search_type = "similarity"

    elif is_technical and not is_personal:
        search_kwargs = {
            "k": 4,
            "filter": {"type": "technical"}
        }
        search_type = "mmr"

    elif is_personal and not is_personal:
        search_kwargs = {
            "k": 4,
            "filter": {"type": "personal"}
        }
        search_type = "similarity"

    else:
    # default to personal since most of vault is personal
        search_kwargs = {
            "k": 4,
            "filter": {"type": "personal"}
        }
        search_type = "mmr"

    return vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs
    )
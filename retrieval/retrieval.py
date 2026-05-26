import re
from datetime import datetime
from langchain_core.runnables import RunnableLambda

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


def _extract_dates_from_metadata(metadata):
    # Return normalized dates from metadata as exact tokens (not substrings).
    dates = []
    all_dates = metadata.get("all_dates", "")

    if isinstance(all_dates, str) and all_dates.strip():
        dates.extend([d.strip() for d in all_dates.split(",") if d.strip()])

    primary_date = metadata.get("date")
    if isinstance(primary_date, str) and primary_date.strip() and primary_date != "unknown":
        dates.append(primary_date.strip())

    return {normalize_date(d) for d in dates}


def _date_filtered_retriever(vectorstore, normalized_date):
    # Retrieve broadly, then enforce exact date membership in Python.
    base_retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 20}
    )

    def _invoke(query):
        docs = base_retriever.invoke(query)
        filtered = [
            doc for doc in docs
            if normalized_date in _extract_dates_from_metadata(doc.metadata)
        ]
        return filtered[:6]

    return RunnableLambda(_invoke)

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
        return _date_filtered_retriever(vectorstore, normalized)

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

    elif is_personal and not is_technical:
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
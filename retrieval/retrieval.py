from datetime import datetime
import re

def parse_date(date_str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return date_str  # fallback if parsing fails

TECHNICAL_FOLDERS = ["cloud", "dsa", "webd", "projects", "rags"] # Add your own if needed

PERSONAL_KEYWORDS = [ # Add your own if needed
    "poem", "letter", "diary", "journal", "wrote", "writing",
    "feel", "feeling", "felt", "emotion", "personal", "art",
    "dream", "memory", "memories", "thought", "story", "unsent",
]

TECHNICAL_KEYWORDS = [
    "code", "function", "array", "algorithm", "database", "server",
    "cloud", "aws", "docker", "html", "css", "javascript", "python",
    "dsa", "web", "api", "bug", "error", "class", "loop"
]
def retrieve(vectorstore, query):
    query_lower = query.lower()

    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b', query)
    is_personal = any(word in query_lower for word in PERSONAL_KEYWORDS)
    is_technical = any(word in query_lower for word in TECHNICAL_KEYWORDS)

    if date_match:
        normalized_date = parse_date(date_match.group(1))

        search_kwargs = {
            "k": 4,
            "filter": {"date": normalized_date}
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
        search_kwargs = {"k": 4}
        search_type = "mmr"

    return vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs
    )
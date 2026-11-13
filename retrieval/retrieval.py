import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from indexing.load import load_file

# Whole notes above this size fall back to chunk search within the note, so the prompt stays
# well inside the chat model's context window (~4 chars per token, NUM_CTX = 8192 tokens)
MAX_WHOLE_FILE_CHARS = 16000

TECHNICAL_FOLDERS = ["cloud", "dsa", "webd", "projects", "rags"]

PERSONAL_KEYWORDS = [
    "poem", "letter", "diary", "journal", "wrote", "writing",
    "feel", "feeling", "felt", "emotion", "personal", "art",
    "dream", "memory", "memories", "thought", "story", "unsent",
    "issue", "issues", "problem", "struggle", "conflict",
    "worried", "worry", "anxiety", "sad", "happy", "angry",
    "frustrated", "confused", "lost", "stuck", "my", "i am",
    "im", "i've", "ive", "i feel", "i think", "i want", "i need",
    "life", "maybe"
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


MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}
# longest first so "sept" wins over "sep"; (?![a-z]) stops "may" matching inside "maybe"
# while still allowing note-name style dates like "20july2026"
_MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")(?![a-z])\.?"
_ORD = r"(?:st|nd|rd|th)?"

_DATE_PATTERNS = [
    # 20/07/2026, 20-07-2026, 20.07.2026 (day first, matching how notes are indexed)
    ("dmy", re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")),
    # 2026-07-20
    ("ymd", re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")),
    # 20 july 2026, 20th of July, 20july2026, 1 sept
    ("d_month_y", re.compile(rf"\b(\d{{1,2}}){_ORD}\s*(?:of\s+)?{_MONTH}(?:,?\s*(\d{{4}}))?", re.I)),
    # July 20, 2026 / July 20th
    ("month_d_y", re.compile(rf"\b{_MONTH}\s+(\d{{1,2}}){_ORD}\b(?:,?\s*(\d{{4}}))?", re.I)),
]

# Month names that are also everyday words ("may 5 people", "march 3 miles") only count
# as a month-first date when a year is given
_AMBIGUOUS_MONTHS = {"may", "mar", "march"}


def extract_date(query, today=None):
    """Return (day, month, year_or_None) for the first date mentioned in the query, else None.

    Understands numeric dates, written-out dates in either order, ordinals, abbreviations and
    "today"/"yesterday". Impossible dates (31 June) are ignored.
    """
    today = today or date.today()
    lowered = query.lower()

    if re.search(r"\bday before yesterday\b", lowered):
        d = today - timedelta(days=2)
        return d.day, d.month, d.year
    if re.search(r"\byesterday\b", lowered):
        d = today - timedelta(days=1)
        return d.day, d.month, d.year
    if re.search(r"\btoday\b", lowered):
        return today.day, today.month, today.year

    for kind, pattern in _DATE_PATTERNS:
        for match in pattern.finditer(lowered):
            if kind == "dmy":
                day, month, year = int(match[1]), int(match[2]), int(match[3])
            elif kind == "ymd":
                year, month, day = int(match[1]), int(match[2]), int(match[3])
            elif kind == "d_month_y":
                day, month = int(match[1]), MONTHS[match[2]]
                year = int(match[3]) if match[3] else None
            else:
                if match[1] in _AMBIGUOUS_MONTHS and not match[3]:
                    continue
                month, day = MONTHS[match[1]], int(match[2])
                year = int(match[3]) if match[3] else None

            try:
                # 2000 is a leap year, so a year-less 29 Feb still validates
                date(year or 2000, month, day)
            except ValueError:
                continue
            return day, month, year

    return None


def notes_on_date(vectorstore, when):
    """Return the filenames of notes dated `when` = (day, month, year_or_None).

    Looks the date up directly in note metadata instead of filtering similarity results,
    which missed entries that weren't among the nearest matches. Notes whose main date is the
    requested day come first, then notes that merely mention it. Without a year, the most recent
    year that has a note for that day is used.
    """
    day, month, year = when
    primary = defaultdict(set)
    mentioned = defaultdict(set)

    for meta in vectorstore.get(include=["metadatas"])["metadatas"]:
        filename = meta.get("filename")
        if not filename:
            continue
        if meta.get("date") not in (None, "unknown"):
            primary[normalize_date(meta["date"])].add(filename)
        for d in _extract_dates_from_metadata(meta):
            mentioned[d].add(filename)

    if year:
        key = f"{day:02d}/{month:02d}/{year}"
    else:
        prefix = f"{day:02d}/{month:02d}/"
        years = [k for k in mentioned if k.startswith(prefix) and k[-4:].isdigit()]
        key = max(years, key=lambda k: int(k[-4:]), default=None)

    if not key:
        return []
    main = sorted(primary.get(key, ()))
    return main + sorted(mentioned.get(key, set()) - set(main))


# Lowercase, treat _ and - as spaces, drop punctuation, collapse whitespace, so
# "javascript_crud_must_know" and "What's in 'The final unsent letter'?" compare cleanly
def _normalize_name(text):
    text = re.sub(r'[_\-]+', ' ', text.lower())
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def match_filename(vectorstore, query):
    """Return the indexed filename the query refers to, or None.

    Compares the query against the filenames that actually exist in the vault rather than
    guessing from sentence structure. A leading article is optional ("final unsent letter"
    matches "The final unsent letter"). Single-word names like "docker" or "Node" only count
    when quoted, since as bare words they're usually topics, not references to one note.
    The longest match wins.
    """
    normalized_query = _normalize_name(query)
    quoted = {_normalize_name(term) for term in re.findall(r'["\']([^"\']+)["\']', query)}

    filenames = {meta.get("filename") for meta in vectorstore.get(include=["metadatas"])["metadatas"]}

    best = None
    for filename in filenames:
        if not filename:
            continue
        name = _normalize_name(filename)
        short_name = re.sub(r'^(the|a|an) ', '', name)

        if name in quoted or short_name in quoted:
            matched = True
        elif len(short_name.split()) < 2:
            matched = False
        else:
            matched = re.search(rf'\b{re.escape(short_name)}\b', normalized_query) is not None

        if matched and (best is None or len(name) > len(_normalize_name(best))):
            best = filename

    return best


def find_target_notes(vectorstore, query):
    """Notes the query points at directly, by name or by date. Empty if neither."""
    filename = match_filename(vectorstore, query)
    if filename:
        return [filename]

    when = extract_date(query)
    return notes_on_date(vectorstore, when) if when else []


def load_whole_files(vectorstore, filenames):
    """Return the full notes with these filenames read fresh from disk, or None.

    Reading the file itself instead of stitching chunks back together gives the model the
    exact text in order, with no gaps or duplicated chunk overlap, which matters when asked
    to reproduce a poem or letter. Notes are added in order until MAX_WHOLE_FILE_CHARS; one
    that doesn't fit is skipped. None means nothing fit, so the caller should fall back to
    searching inside these notes.
    """
    docs = []
    used = 0
    for filename in filenames:
        metadatas = vectorstore.get(where={"filename": filename}, include=["metadatas"])["metadatas"]
        for source in sorted({meta["source"] for meta in metadatas}):
            loaded = load_file(source) or []
            size = sum(len(doc.page_content) for doc in loaded)
            if loaded and used + size <= MAX_WHOLE_FILE_CHARS:
                docs.extend(loaded)
                used += size

    return docs or None


def retrieve(vectorstore, query, filenames=None):
    query_lower = query.lower()

    is_personal = any(word in query_lower for word in PERSONAL_KEYWORDS)
    is_technical = any(word in query_lower for word in TECHNICAL_KEYWORDS)

    if filenames:
        # notes named or dated in the query but too large to send whole: search within them only
        search_kwargs = {
            "k": 6,
            "filter": {"filename": {"$in": list(filenames)}}
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
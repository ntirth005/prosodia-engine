import re
from typing import List, Pattern

# --- Configuration / tunables ---
ABBREVIATIONS = [
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.",
    "St.", "vs.", "e.g.", "i.e.", "etc.", "U.S.", "U.K.", "Ph.D.", "No."
]

# Conjunctions that often start new clause/phrase; kept with the second phrase
CONJUNCTIONS = [
    "but", "however", "although", "because", "while", "yet",
    "and", "so", "therefore", "though", "unless"
]

# Maximum words allowed in a phrase before we force a split (attempt)
MAX_WORDS = 10
MIN_WORDS = 2  # avoid creating phrases shorter than this unless forced

# Characters considered splitting punctuation within sentences
INTERNAL_SPLIT_PUNCT = r"[,:;]"

# --- Helpers ---


def _protect_abbreviations(text: str, abbrs: List[str]) -> (str, dict):
    """
    Replace '.' inside known abbreviations with a placeholder so sentence
    splitting won't break them. Returns transformed text and a map for restore.
    """
    placeholder = "<DOT>"
    restore_map = {}
    t = text
    for i, a in enumerate(sorted(abbrs, key=len, reverse=True)):  # longer first
        escaped = re.escape(a)
        # match case-insensitive but restore original case later
        def repl(match: re.Match):
            orig = match.group(0)
            protected = orig.replace(".", placeholder)
            key = f"__ABBR_{i}__"
            restore_map[key] = protected
            return key

        # Use word boundary-aware replace to avoid mid-word matches
        t = re.sub(escaped, repl, t, flags=re.IGNORECASE)
    return t, restore_map


def _restore_abbreviations(text: str, restore_map: dict) -> str:
    t = text
    for key, protected in restore_map.items():
        t = t.replace(key, protected.replace("<DOT>", "."))
    return t


def _split_sentences(paragraph: str) -> List[str]:
    """
    Split paragraph into sentences using . ? ! but avoid splitting inside protected
    abbreviations (we protect them before calling this). Trailing punctuation removed.
    """
    # split on end-of-sentence punctuation followed by whitespace
    # keep the punctuation with sentence for clarity then strip later
    parts = re.split(r'(?<=[.!?])\s+', paragraph)
    # remove trailing sentence-ending punctuation for the phrase splitting steps
    sentences = [p.strip() for p in parts if p.strip()]
    # strip trailing sentence terminator for uniform further processing
    sentences = [re.sub(r'[.!?]\s*$', '', s).strip() for s in sentences]
    return sentences


def _split_on_internal_punctuation(sentence: str) -> List[str]:
    """
    Split on commas, semicolons, colons (short pauses in speech).
    Remove the splitting punctuation from output phrases.
    """
    # Split on punctuation and keep only text parts
    parts = re.split(INTERNAL_SPLIT_PUNCT, sentence)
    parts = [p.strip() for p in parts if p and p.strip()]
    return parts


def _split_on_conjunctions(phrase: str, conj_pattern: Pattern) -> List[str]:
    """
    Split phrase where a conjunction introduces a new clause.
    The conjunction must be kept with the second phrase.
    """
    # Split with lookahead so the conjunction starts the next piece.
    # Use case-insensitive splitting; re.split will remove the matched boundary,
    # so we will re-attach the conjunction to the start of the following piece.
    pieces = re.split(r'\s+(?={})'.format(conj_pattern.pattern), phrase, flags=re.IGNORECASE)
    # re.split with lookahead yields pieces where matches are not removed,
    # but because we used lookahead, the conjunction stays with the second piece
    # (we included it in the lookahead condition).
    return [p.strip() for p in pieces if p and p.strip()]


def _count_words(s: str) -> int:
    return len([w for w in re.findall(r"\b\w+\b", s)])


def _force_split_long_phrase(phrase: str, max_words: int, conj_pattern: Pattern) -> List[str]:
    """
    If phrase length > max_words, try to split:
     - prefer splitting at a conjunction inside the phrase (closest to middle)
     - else split roughly in half (between words), avoiding very short pieces
    """
    words = re.findall(r"\S+", phrase)
    if len(words) <= max_words:
        return [phrase.strip()]

    # 1) try to find conjunction inside phrase (excluding when it's first word)
    conj_matches = list(re.finditer(r'\b({})\b'.format(conj_pattern.pattern), phrase, flags=re.IGNORECASE))
    if conj_matches:
        # pick the match nearest to the middle of the phrase (by word index)
        word_positions = []
        for m in conj_matches:
            # find word index of match start by counting words before it
            pre = phrase[:m.start()]
            idx = _count_words(pre)
            word_positions.append((abs(idx - len(words) // 2), m))
        # choose the conj nearest middle
        _, chosen = min(word_positions, key=lambda x: x[0])
        split_pos = chosen.start()
        left = phrase[:split_pos].strip()
        right = phrase[split_pos:].strip()
        # ensure both parts are reasonable length; if one side is too short, fallback
        if MIN_WORDS <= _count_words(left) <= max_words and MIN_WORDS <= _count_words(right) <= max_words:
            return [left, right]
        # If the right side is too long, recursively split it
        result = []
        if left:
            result.append(left)
        result.extend(_force_split_long_phrase(right, max_words, conj_pattern))
        return result

    # 2) fallback: split roughly in the middle by words, avoiding ultra-short parts
    mid = len(words) // 2
    # try to pick a split point near mid that yields both parts >= MIN_WORDS
    for offset in range(0, len(words)):
        for candidate in (mid - offset, mid + offset):
            if candidate <= 0 or candidate >= len(words):
                continue
            left_words = words[:candidate]
            right_words = words[candidate:]
            if len(left_words) >= MIN_WORDS and len(right_words) >= MIN_WORDS:
                left = " ".join(left_words)
                right = " ".join(right_words)
                # Further force-split right if still too long
                res = [left]
                res.extend(_force_split_long_phrase(right, max_words, conj_pattern))
                return res

    # As a last resort, just return the phrase (can't split reasonably)
    return [phrase.strip()]


# Precompile conjunction regex pattern
CONJ_PATTERN = re.compile("|".join(re.escape(c) for c in CONJUNCTIONS), flags=re.IGNORECASE)


def split_into_phrases(paragraph: str, *,
                       abbreviations: List[str] = None,
                       conjunctions_pattern: Pattern = CONJ_PATTERN,
                       max_words: int = MAX_WORDS) -> List[str]:
    """
    Main API: split a paragraph into speech-friendly phrases.
    Returns a list of phrase strings in original order (trimmed).
    """
    abbreviations = abbreviations or ABBREVIATIONS

    # 1) Normalize whitespace
    text = re.sub(r'\s+', ' ', paragraph).strip()
    if not text:
        return []

    # 2) Protect abbreviations so sentence splitting won't break them
    protected_text, restore_map = _protect_abbreviations(text, abbreviations)

    # 3) Sentence segmentation
    sentences = _split_sentences(protected_text)
    # restore abbreviations inside sentences
    sentences = [_restore_abbreviations(s, restore_map) for s in sentences]

    final_phrases: List[str] = []

    for sent in sentences:
        if not sent:
            continue
        # 4) Split on internal pause punctuation (comma/semicolon/colon)
        parts = _split_on_internal_punctuation(sent)

        for part in parts:
            if not part:
                continue

            # 5) Split on conjunction boundaries (conjunction should stay with following phrase)
            conj_splits = re.split(r'(?i)\s+(?=(?:' + "|".join(re.escape(c) for c in CONJUNCTIONS) + r')\b)', part)
            # re.split with lookahead keeps the conjunction at start of next piece

            # Clean and process each conj_split further
            for chunk in conj_splits:
                chunk = chunk.strip()
                if not chunk:
                    continue

                # 6) Enforce phrase length constraint: if too long, attempt splits
                if _count_words(chunk) > max_words:
                    # attempt to split using conjunctions first, then force split
                    # first, attempt splitting by conjunctions inside the chunk
                    sub_splits = re.split(r'(?i)\s+(?=(?:' + "|".join(re.escape(c) for c in CONJUNCTIONS) + r')\b)', chunk)
                    if len(sub_splits) > 1:
                        for ss in sub_splits:
                            ss = ss.strip()
                            if not ss:
                                continue
                            if _count_words(ss) > max_words:
                                final_phrases.extend(_force_split_long_phrase(ss, max_words, conjunctions_pattern))
                            else:
                                final_phrases.append(ss)
                    else:
                        # no conjunction, force split roughly
                        final_phrases.extend(_force_split_long_phrase(chunk, max_words, conjunctions_pattern))
                else:
                    final_phrases.append(chunk)

    # 7) Clean up: trim whitespace and remove empty phrases; strip splitting punctuation from edges
    cleaned = []
    for p in final_phrases:
        # remove leading/trailing punctuation that came from splitting (but keep internal punctuation)
        p2 = p.strip()
        p2 = re.sub(r'^[\s"\'(\[]+|[\s"\')\].,;:!?]+$', '', p2)
        if p2:
            cleaned.append(p2)

    return cleaned


# --- Quick test / examples ---
if __name__ == "__main__":
    examples = [
        ("I am really sorry for the delay, but we will fix this immediately and keep you updated.",
         ["I am really sorry for the delay", "but we will fix this immediately", "and keep you updated"]),

        ("Dr. Smith arrived late. The meeting had already started.",
         ["Dr. Smith arrived late", "The meeting had already started"]),

        ("Although the system performed well during testing, we noticed a few issues, and the team will investigate them tomorrow.",
         ["Although the system performed well during testing", "we noticed a few issues", "and the team will investigate them tomorrow"]),

        ("The system processed the request successfully and returned the result to the client within seconds.",
         # Possible acceptable segmentation
         ["The system processed the request successfully", "and returned the result", "to the client within seconds"])
    ]

    for text, expected in examples:
        out = split_into_phrases(text)
        print("INPUT: ", text)
        print("OUTPUT:", out)
        print("EXPECTED (example):", expected)
        print("---")
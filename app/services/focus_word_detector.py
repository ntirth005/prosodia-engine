import re
from typing import List, Dict

# Emotion / emphasis lexicon organised by category.
# Each category groups words that share a communicative intent, making it
# straightforward to extend or tune individual emotion classes independently.
FOCUS_LEXICON_BY_CATEGORY: Dict[str, set] = {
    # Words that convey apology or remorse
    "apology": {
        "sorry", "apologize", "apologies", "regret", "unfortunately",
        "forgive", "pardon", "excuse",
    },
    # Words that convey time-pressure or danger
    "urgency": {
        "urgent", "urgently", "immediately", "asap", "critical",
        "emergency", "warning", "alert", "deadline", "now",
    },
    # Words that convey comfort, confidence, or positive resolution
    "reassurance": {
        "resolved", "fixed", "guaranteed", "assure", "promise",
        "certainly", "definitely", "absolutely", "confirmed",
        "safe", "secure", "handled",
    },
    # Words that convey enthusiasm or positive surprise
    "excitement": {
        "amazing", "great", "fantastic", "wonderful", "excellent",
        "outstanding", "brilliant", "incredible", "awesome", "success",
        "celebrate", "thrilled",
    },
    # Words that signal high significance
    "importance": {
        "important", "essential", "necessary", "required", "must",
        "vital", "significant", "major", "key", "critical",
        "crucial", "priority",
    },
    # Words that describe a negative outcome or problem
    "negative_outcome": {
        "fail", "failed", "failure", "error", "broken", "problem",
        "issue", "delay", "wrong", "bad", "terrible", "unacceptable",
    },
    # Words that indicate an action is pending or required
    "action_required": {
        "fix", "update", "review", "check", "confirm", "respond",
        "contact", "report", "address", "investigate",
    },
}

# Flat set built from all categories — used for O(1) per-token lookup.
FOCUS_LEXICON: set = {
    word
    for words in FOCUS_LEXICON_BY_CATEGORY.values()
    for word in words
}


def tokenize(text: str) -> List[str]:
    """Extract individual word tokens from *text*, preserving original casing."""
    return re.findall(r"\b\w+\b", text)


def detect_focus_words(phrase: str) -> Dict:
    """Identify emphasis-worthy words in a single *phrase*.

    Each token is normalised to lowercase before lookup so the lexicon entries
    are case-insensitive, but the original surface form is preserved in the
    output to keep the result aligned with the source text.

    Returns a dict with two keys:
        ``phrase``       – the original phrase string, unchanged.
        ``focus_words``  – list of matched tokens in the order they appear in
                           the phrase (duplicates are kept if a word appears
                           more than once).
    """
    words = tokenize(phrase)
    focus_words = [word for word in words if word.lower() in FOCUS_LEXICON]
    return {
        "phrase": phrase,
        "focus_words": focus_words,
    }


def detect_focus_for_phrases(phrases: List[str]) -> List[Dict]:
    """Run :func:`detect_focus_words` over every phrase in *phrases*.

    The returned list is the same length as *phrases* and its order matches,
    so results stay aligned with upstream pipeline stages (phrase splitter,
    emotion classifier).
    """
    return [detect_focus_words(phrase) for phrase in phrases]
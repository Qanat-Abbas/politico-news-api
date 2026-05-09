from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "because",
    "been",
    "but",
    "can",
    "could",
    "did",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "her",
    "his",
    "how",
    "into",
    "its",
    "more",
    "not",
    "now",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "was",
    "were",
    "what",
    "when",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
}


def summarize(text: str, keyword: str, max_sentences: int = 3) -> str:
    clean_text = _normalize_space(text)
    if not clean_text:
        return "No readable article text was available to summarize."

    sentences = _split_sentences(clean_text)
    if not sentences:
        return _limit(clean_text)
    if len(sentences) <= max_sentences:
        return _limit(" ".join(sentences))

    word_counts = _word_counts(sentences)
    if not word_counts:
        return _limit(" ".join(sentences[:max_sentences]))

    keyword_terms = set(_words(keyword))
    scored = []
    for index, sentence in enumerate(sentences):
        words = _words(sentence)
        if len(words) < 6:
            continue

        frequency_score = sum(word_counts[word] for word in words) / len(words)
        keyword_score = 2.0 if keyword_terms.intersection(words) else 0.0
        length_penalty = 0.25 if len(sentence) > 320 else 0.0
        scored.append((frequency_score + keyword_score - length_penalty, index, sentence))

    if not scored:
        return _limit(" ".join(sentences[:max_sentences]))

    selected = sorted(scored, reverse=True)[:max_sentences]
    ordered_sentences = [sentence for _score, _index, sentence in sorted(selected, key=lambda row: row[1])]
    return _limit(" ".join(ordered_sentences))


def _split_sentences(text: str) -> list[str]:
    rough_sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = []
    seen = set()
    for sentence in rough_sentences:
        cleaned = sentence.strip()
        key = re.sub(r"\W+", "", cleaned.lower())
        if len(cleaned) >= 35 and key not in seen:
            seen.add(key)
            sentences.append(cleaned)
    return sentences


def _word_counts(sentences: list[str]) -> Counter[str]:
    words = []
    for sentence in sentences:
        words.extend(word for word in _words(sentence) if word not in STOPWORDS and len(word) > 2)
    return Counter(words)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z'-]+", text.lower())


def _normalize_space(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def _limit(text: str, limit: int = 900) -> str:
    if len(text) <= limit:
        return text

    truncated = text[:limit].rsplit(" ", 1)[0].rstrip()
    return f"{truncated}..."

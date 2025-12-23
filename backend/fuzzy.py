"""
Fuzzy matching utilities for contacts, vendors, aliases.
Uses normalize + token overlap + difflib for similarity.
"""
import re
import unicodedata
from difflib import get_close_matches
from typing import List, Optional, Tuple


def normalize(text: str) -> str:
    """Normalize text: lowercase, strip accents, remove punctuation."""
    if not text:
        return ""
    # Lowercase
    text = text.lower().strip()
    # Remove accents
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Remove punctuation except spaces
    text = re.sub(r"[^\w\s]", "", text)
    return text


def tokenize(text: str) -> List[str]:
    """Split normalized text into tokens."""
    return normalize(text).split()


def token_overlap(query: str, target: str) -> float:
    """
    Return overlap ratio between query and target tokens.
    1.0 = all query tokens found in target.
    """
    q_tokens = set(tokenize(query))
    t_tokens = set(tokenize(target))
    if not q_tokens:
        return 0.0
    matched = q_tokens & t_tokens
    return len(matched) / len(q_tokens)


def contains_match(query: str, target: str) -> bool:
    """Check if normalized query is contained in normalized target or vice versa."""
    q = normalize(query)
    t = normalize(target)
    return q in t or t in q


def fuzzy_match(query: str, candidates: List[str], cutoff: float = 0.6) -> List[Tuple[str, float]]:
    """
    Return matching candidates with scores.
    Uses multiple strategies:
    1. Exact contains match (score 1.0)
    2. Token overlap (score = overlap ratio)
    3. difflib similarity (score from get_close_matches)

    Returns list of (candidate, score) sorted by score desc.
    """
    results = []
    q_norm = normalize(query)

    for candidate in candidates:
        c_norm = normalize(candidate)

        # Exact contains
        if q_norm in c_norm or c_norm in q_norm:
            results.append((candidate, 1.0))
            continue

        # Token overlap
        overlap = token_overlap(query, candidate)
        if overlap >= cutoff:
            results.append((candidate, overlap))
            continue

        # Difflib fuzzy
        matches = get_close_matches(q_norm, [c_norm], n=1, cutoff=cutoff)
        if matches:
            # Calculate rough similarity score
            score = 1 - (len(set(q_norm) ^ set(c_norm)) / max(len(q_norm), len(c_norm), 1))
            results.append((candidate, max(score, cutoff)))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def best_match(query: str, candidates: List[str], cutoff: float = 0.6) -> Optional[str]:
    """Return best matching candidate or None."""
    matches = fuzzy_match(query, candidates, cutoff)
    return matches[0][0] if matches else None


def extract_potential_names(text: str) -> List[str]:
    """
    Extract potential entity names from user query.
    Handles: "facture Distram", "mail de Céline", "la comptable", etc.
    """
    text = text.strip()
    names = []

    # Pattern: "de/from X" or "X's"
    patterns = [
        r"(?:de|from|par)\s+([A-ZÀ-Ÿa-zà-ÿ][\w\-]+(?:\s+[\w\-]+)?)",
        r"(?:facture|invoice|mail|email|message)\s+([A-ZÀ-Ÿ][\w\-]+)",
        r"([A-ZÀ-Ÿ][\w\-]+(?:\s+[A-ZÀ-Ÿ][\w\-]+)?)",  # Capitalized words
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(1).strip()
            # Filter common words
            if name.lower() not in {"le", "la", "les", "un", "une", "des", "du", "de", "mon", "ma", "mes"}:
                names.append(name)

    # Also try each word that looks like a proper noun
    words = text.split()
    for word in words:
        clean = re.sub(r"[^\w]", "", word)
        if clean and clean[0].isupper() and len(clean) > 2:
            if clean.lower() not in {"le", "la", "les", "un", "une", "des"}:
                names.append(clean)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for n in names:
        n_lower = n.lower()
        if n_lower not in seen:
            seen.add(n_lower)
            unique.append(n)

    return unique

"""Deterministic Hindi rendering helpers for the Evidence Packet (Req 14.7).

Offline, template-based translation for the fixed set of packet headings/summary
labels and the issue themes, plus a best-effort per-quote Hindi translation
built from a small glossary. Output is labelled template-generated to be honest
about the fallback (no live MT in the sandbox).
"""

from __future__ import annotations

# Fixed packet labels -> Devanagari.
LABELS_HI: dict[str, str] = {
    "Evidence Packet": "साक्ष्य पैकेट",
    "Destination": "गंतव्य",
    "Date range": "तिथि सीमा",
    "Issue theme": "समस्या विषय",
    "Total mentions": "कुल उल्लेख",
    "Distinct properties": "विशिष्ट संपत्तियाँ",
    "Monthly trend": "मासिक रुझान",
    "Representative quotes": "प्रतिनिधि उद्धरण",
    "Map excerpt": "मानचित्र अंश",
    "Summary": "सारांश",
    "Generated for authorities": "अधिकारियों के लिए तैयार",
}

THEME_HI: dict[str, str] = {
    "traffic": "यातायात",
    "parking": "पार्किंग",
    "water": "पानी",
    "garbage": "कचरा",
    "road condition": "सड़क की स्थिति",
    "safety": "सुरक्षा",
}

# Small glossary for a best-effort per-quote Hindi gloss (word-level).
_GLOSSARY: dict[str, str] = {
    "road": "सड़क",
    "roads": "सड़कें",
    "traffic": "यातायात",
    "parking": "पार्किंग",
    "water": "पानी",
    "garbage": "कचरा",
    "trash": "कचरा",
    "safety": "सुरक्षा",
    "unsafe": "असुरक्षित",
    "dirty": "गंदा",
    "bad": "खराब",
    "poor": "खराब",
    "problem": "समस्या",
    "mall": "माल",
    "mussoorie": "मसूरी",
    "near": "के पास",
    "the": "",
    "was": "था",
    "is": "है",
    "very": "बहुत",
    "and": "और",
    "no": "नहीं",
    "too": "बहुत",
    "much": "ज़्यादा",
    "crowded": "भीड़भाड़",
    "jam": "जाम",
    "potholes": "गड्ढे",
    "pothole": "गड्ढा",
}


def label_hi(label: str) -> str:
    """Return the Devanagari label for a known packet heading."""
    return LABELS_HI.get(label, label)


def theme_hi(theme: str) -> str:
    """Return the Devanagari form of an issue theme."""
    return THEME_HI.get(theme, theme)


def translate_quote_hi(text: str) -> str:
    """Best-effort Hindi gloss of ``text`` (template-generated, Req 14.7).

    If the text is already Devanagari it is returned unchanged. Otherwise each
    known word is glossed; unknown words are kept so the gloss stays readable.
    """
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return text  # already Hindi/Devanagari
    out: list[str] = []
    for raw in text.split():
        token = raw.strip(".,!?;:\"'()[]").lower()
        gloss = _GLOSSARY.get(token)
        if gloss:
            out.append(gloss)
        elif gloss == "":
            continue
        else:
            out.append(raw)
    return " ".join(out) + " (मशीन-अनुवाद)"

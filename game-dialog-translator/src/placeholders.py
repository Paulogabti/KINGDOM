from __future__ import annotations

import re
from dataclasses import dataclass

FIXED = {
    "NI","WO","CH","TA","NTA","ABC","ME","CITY","ITEM","PLACE","PLACE1NAME","PLACE2NAME",
    "SN1MING","SN2MING","SN3MING","SN1CH","SN2CH","SN3CH","AMING","NMING","NIMNG","WOAMING"
}

PATTERNS = [
    r"\{[A-Za-z0-9_]+\}",
    r"%\.?\d*[sdf]",
    r"</?[A-Za-z][^>]*>",
    r"\\[rnt]",
    r"\[[A-Za-z0-9_]+(?:=[^\]]+)?\]",
    r"\b[A-Z]{2,}\b",
    r"\b[A-Z]+\d+[A-Z0-9]*\b",
]

@dataclass
class ProtectedText:
    text: str
    mapping: dict[str, str]


def protect_placeholders(text: str) -> ProtectedText:
    mapping: dict[str, str] = {}
    i = 1
    tokens = set(FIXED)
    for p in PATTERNS:
        tokens.update(re.findall(p, text))
    for token in sorted(tokens, key=len, reverse=True):
        if not token or token not in text:
            continue
        ph = f"__PH_{i:04d}__"
        text = text.replace(token, ph)
        mapping[ph] = token
        i += 1
    return ProtectedText(text=text, mapping=mapping)


def restore_placeholders(text: str, mapping: dict[str, str]) -> str:
    out = text
    for ph, token in mapping.items():
        out = out.replace(ph, token)
    return out


def placeholders_preserved(restored_text: str, mapping: dict[str, str]) -> bool:
    return all(tok in restored_text for tok in mapping.values())

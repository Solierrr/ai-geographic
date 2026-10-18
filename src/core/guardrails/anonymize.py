import re
import uuid

PII_PATTERNS = [
    ("CNPJ", r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"),
    ("CPF", r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
    ("TELEFONE", r"(?<!\d)(?:\+55\s?)?\(?\d{2}\)?[\s-]?9\d{4}-\d{4}(?!\d)"),
    ("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
]


def anonymize_text(text: str):
    pii_map = {}
    for pii_type, pattern in PII_PATTERNS:
        matches = set(re.findall(pattern, text))
        for value in matches:
            token = f"[PII_{pii_type}_{uuid.uuid4().hex[:6]}]"
            pii_map[token] = value
            text = text.replace(value, token)
    return text, pii_map


def deanonymize_text(text: str, pii_map: dict) -> str:
    for token, value in pii_map.items():
        if token in text:
            text = text.replace(token, f"[{token.split('_')[1]} OMITIDO]")
    return text

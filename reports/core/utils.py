import re

def normalize_text(text: str) -> str:
    """Normaliza o texto para análise, removendo pontuação e convertendo para minúsculas."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[\.\?,!;"]", "", text)
    return text


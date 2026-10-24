"""Small source utilities shared by this public-code audit's controls."""
import re


def mask_noncode(text):
    """Keep byte/line offsets while blanking comments and character/string data."""
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda match: re.sub(r"[^\n]", " ", match.group()), text)


def function(text, signature):
    start = text.index(signature + "\n{")
    masked = mask_noncode(text)
    at = masked.index("{", start)
    depth, end = 1, at + 1
    while depth:
        depth += (masked[end] == "{") - (masked[end] == "}")
        end += 1
    return text[start:end]

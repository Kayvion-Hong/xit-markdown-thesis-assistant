"""Align Pandoc block text to source lines; PDF positions use named destinations.

Text alignment is deliberately paragraph/block-level. Unmatched blocks are omitted
instead of inventing a source position. PDF coordinates themselves are not guessed.
"""
from difflib import SequenceMatcher
import hashlib
import unicodedata
import json
import re


def normalize(text):
    chars, lines = [], []
    line = 1
    for char in text:
        for value in unicodedata.normalize('NFKC', char).casefold():
            if value.isalnum():
                chars.append(value)
                lines.append(line)
        if char == '\n':
            line += 1
    return ''.join(chars), lines


def align(source, relative, records):
    plain, line_numbers = normalize(source)
    source_lines = source.splitlines()
    chunks = [normalize(record['text'])[0] for record in records]
    generated = ''.join(chunks)
    matches = SequenceMatcher(None, generated, plain, autojunk=False).get_matching_blocks()
    output, offset = [], 0
    for record, chunk in zip(records, chunks):
        hits = []
        for match in matches:
            start, end = max(offset, match.a), min(offset + len(chunk), match.a + match.size)
            if end > start:
                hits.extend(range(match.b + start - match.a, match.b + end - match.a))
        if chunk and len(hits) / len(chunk) >= 0.55:
            first, last = line_numbers[hits[0]], line_numbers[hits[-1]]
            if record['kind'] == 'CodeBlock':
                for index in range(first - 2, -1, -1):
                    fence = re.match(r'^\s*(`{3,}|~{3,})', source_lines[index])
                    if fence:
                        first = index + 2
                        for end in range(last, len(source_lines)):
                            if re.match(r'^\s*' + re.escape(fence[1]) + r'\s*$', source_lines[end]):
                                last = end
                                break
                        break
            output.append({
                'anchor': record['anchor'], 'path': relative,
                'start': first, 'end': last,
                'kind': record['kind'], 'search': chunk,
            })
        offset += len(chunk)
    return output


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def brace_groups(text):
    """Read top-level TeX groups, allowing nested formatting in heading titles."""
    depth, start, output = 0, 0, []
    for index, char in enumerate(text):
        if index and text[index-1] == '\\':
            continue
        if char == '{':
            if depth == 0:
                start = index + 1
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                output.append(text[start:index])
    return output


def resolve_headers(project):
    """Pandoc emits heading labels; resolve their actual hyperref destinations."""
    path = project / 'source-map.json'
    if not path.is_file():
        return
    mapping = json.loads(path.read_text(encoding='utf-8'))
    labels = {}
    for auxiliary in project.rglob('*.aux'):
        for line in auxiliary.read_text(encoding='utf-8', errors='replace').splitlines():
            if not line.startswith('\\newlabel{'):
                continue
            groups = brace_groups(line[len('\\newlabel'):])
            if len(groups) == 2:
                fields = brace_groups(groups[1])
                if len(fields) >= 4:
                    labels[groups[0]] = fields[3]
    for entry in mapping['anchors']:
        if entry['kind'] == 'Header' and entry['anchor'] in labels:
            entry['destination'] = labels[entry['anchor']]
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding='utf-8')

"""Evidence retrieval and provisional, lexical rubric suggestions. Standard library only."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def normalize(text):
    text = unicodedata.normalize('NFD', text.casefold()).replace('đ', 'd')
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')


def tokens(text):
    stop = {'la', 'va', 'cua', 'cho', 'gi', 'nao', 'the', 'a', 'an', 'is', 'what', 'how', 'to', 'in', 'vi', 'sao', 'nhu', 'thi'}
    return set(re.findall(r'\w+', normalize(text))) - stop


def load_course(path):
    course = json.loads(Path(path).read_text(encoding='utf-8'))
    passages = course['passages']
    if len({p['id'] for p in passages}) != len(passages):
        raise ValueError('Duplicate passage IDs')
    by_id = {p['id']: p for p in passages}
    if len({e['id'] for e in course['exercises']}) != len(course['exercises']):
        raise ValueError('Duplicate exercise IDs')
    for exercise in course['exercises']:
        if len({r['id'] for r in exercise['rubric']}) != len(exercise['rubric']):
            raise ValueError('Duplicate rubric IDs')
        for row in exercise['rubric']:
            if row['max_points'] <= 0 or not row['concepts']:
                raise ValueError('Invalid rubric')
            if not all(group and all(isinstance(x, str) and x.strip() for x in group) for group in row['concepts']):
                raise ValueError('Empty concept')
            p = by_id.get(row['source_id'])
            if not p or not row['quote'].strip() or row['quote'] not in p['text']:
                raise ValueError('Rubric evidence is not a literal source quote')
    course['_fingerprint'] = digest(course)
    return course


def retrieve(course, question, limit=3):
    """Lexical overlap only; a score does not establish answerability."""
    q = tokens(question)
    if not q or limit < 1:
        return []
    results = []
    for passage in course['passages']:
        common = q & tokens(passage['title'] + ' ' + passage['text'])
        # Require two overlaps for multi-word queries; still only a lexical heuristic.
        if len(common) >= min(2, len(q)):
            results.append({**passage, 'score': len(common) / len(q)})
    return sorted(results, key=lambda x: (-x['score'], x['id']))[:limit]


def suggest(exercise, answer):
    """Every concept group must match a whole normalized phrase. No semantic claim."""
    text = ' ' + re.sub(r'\W+', ' ', normalize(answer)).strip() + ' '
    rows = []
    for row in exercise['rubric']:
        matches = []
        for alternatives in row['concepts']:
            hit = next((s for s in alternatives if (' ' + re.sub(r'\W+', ' ', normalize(s)).strip() + ' ') in text), None)
            matches.append(hit)
        points = row['max_points'] if answer.strip() and all(matches) else 0
        rows.append({'id': row['id'], 'points': points, 'matched_phrases': matches,
                     'max_points': row['max_points'], 'source_id': row['source_id'], 'quote': row['quote']})
    return {'method': 'lexical_suggestion_requires_human_review', 'rows': rows,
            'suggested_total': sum(r['points'] for r in rows),
            'max_total': sum(r['max_points'] for r in rows)}

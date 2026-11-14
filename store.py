"""Local single-user review ledger; aliases are not authentication."""
import csv
import io
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from core import suggest


def now():
    return datetime.now(timezone.utc).isoformat()


def connect(path='private/tutor.sqlite3'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript('''
    CREATE TABLE IF NOT EXISTS attempts(
      id INTEGER PRIMARY KEY, learner TEXT NOT NULL, exercise TEXT NOT NULL,
      fingerprint TEXT NOT NULL, answer TEXT NOT NULL, suggestion TEXT NOT NULL,
      rubric TEXT NOT NULL, created TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
      review TEXT);
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY, attempt INTEGER, action TEXT, payload TEXT, created TEXT);
    ''')
    return con


def event(con, attempt, action, payload):
    con.execute('INSERT INTO events(attempt,action,payload,created) VALUES(?,?,?,?)',
                (attempt, action, json.dumps(payload, ensure_ascii=False), now()))


def submit(con, learner, course, exercise, answer):
    if not learner.strip() or not answer.strip() or len(answer) > 20000:
        raise ValueError('Nhập mã học viên và câu trả lời (tối đa 20.000 ký tự).')
    result = suggest(exercise, answer)
    with con:
        cursor = con.execute('INSERT INTO attempts(learner,exercise,fingerprint,answer,suggestion,rubric,created) VALUES(?,?,?,?,?,?,?)',
            (learner.strip(), exercise['id'], course['_fingerprint'], answer,
             json.dumps(result, ensure_ascii=False), json.dumps(exercise['rubric'], ensure_ascii=False), now()))
        event(con, cursor.lastrowid, 'submitted', {'course': course['_fingerprint']})
    return cursor.lastrowid


def revise(con, attempt_id, revision, answer):
    if not answer.strip() or len(answer) > 20000:
        raise ValueError('Invalid answer')
    with con:
        con.execute('BEGIN IMMEDIATE')
        old = con.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
        if not old or old['revision'] != revision:
            raise ValueError('Bản ghi đã thay đổi. Hãy tải lại.')
        suggestion = suggest({'rubric': json.loads(old['rubric'])}, answer)
        con.execute('UPDATE attempts SET answer=?,suggestion=?,revision=revision+1,review=NULL WHERE id=?',
                    (answer, json.dumps(suggestion, ensure_ascii=False), attempt_id))
        event(con, attempt_id, 'revised_approval_revoked', {'previous_answer': old['answer'], 'previous_review': old['review']})


def review(con, attempt_id, revision, points, reviewer, feedback):
    if not reviewer.strip() or not feedback.strip():
        raise ValueError('Cần tên người duyệt và phản hồi.')
    with con:
        con.execute('BEGIN IMMEDIATE')
        old = con.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
        if not old or old['revision'] != revision:
            raise ValueError('Bản ghi đã thay đổi. Hãy tải lại.')
        rubric = json.loads(old['rubric'])
        if set(points) != {r['id'] for r in rubric}:
            raise ValueError('Thiếu hoặc thừa tiêu chí')
        for row in rubric:
            value = points[row['id']]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= row['max_points']:
                raise ValueError('Điểm không hợp lệ')
        payload = {'points': points, 'total': sum(points.values()), 'max_total': sum(r['max_points'] for r in rubric),
                   'reviewer': reviewer.strip(), 'feedback': feedback.strip(), 'time': now(), 'revision': revision}
        con.execute('UPDATE attempts SET review=?, revision=revision+1 WHERE id=?', (json.dumps(payload, ensure_ascii=False), attempt_id))
        event(con, attempt_id, 'reviewed', payload)


def attempts(con, learner=None):
    if learner is None:
        return [dict(r) for r in con.execute('SELECT * FROM attempts ORDER BY id')]
    return [dict(r) for r in con.execute('SELECT * FROM attempts WHERE learner=? ORDER BY id', (learner,))]


def progress(con, learner):
    # Latest attempt per exercise AND course version. Unreviewed latest hides old grade.
    latest = {}
    for row in attempts(con, learner):
        latest[(row['fingerprint'], row['exercise'])] = row
    return [{'exercise': r['exercise'], 'course': r['fingerprint'], 'attempt': r['id'],
             'reviewed': bool(r['review']), 'grade': json.loads(r['review']) if r['review'] else None}
            for r in latest.values()]


def csv_export(con, learner):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['learner', 'exercise', 'course_fingerprint', 'attempt', 'total', 'max_total', 'feedback'])
    def safe(value):
        s = str(value)
        return "'" + s if s.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else s
    for item in progress(con, learner):
        if item['reviewed']:
            g = item['grade']
            writer.writerow([safe(x) for x in (learner, item['exercise'], item['course'], item['attempt'], g['total'], g['max_total'], g['feedback'])])
    return '\ufeff' + output.getvalue()

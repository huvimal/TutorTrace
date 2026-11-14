import copy
import json
import tempfile
import unittest
from pathlib import Path
from core import load_course, retrieve, suggest
from store import connect, submit, review, revise, attempts, progress, csv_export
from evaluate import evaluate

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.course = load_course(ROOT / 'data/course.json')
        self.exercise = self.course['exercises'][0]

    def test_fixtures(self):
        report = evaluate()
        self.assertTrue(all(c['passed'] for k in ('retrieval', 'grading') for c in report[k]))

    def test_no_hits(self):
        self.assertEqual(retrieve(self.course, 'địa chất núi lửa'), [])

    def test_empty_question(self):
        self.assertEqual(retrieve(self.course, ''), [])

    def test_returned_quotes_are_literal(self):
        for hit in retrieve(self.course, 'test'):
            self.assertIn(hit['text'], [p['text'] for p in self.course['passages']])

    def test_empty_answer_zero(self):
        self.assertEqual(suggest(self.exercise, '')['suggested_total'], 0)

    def test_phrase_boundaries(self):
        self.assertEqual(suggest(self.exercise, 'training học tham số')['suggested_total'], 0)

    def test_negation_known_limitation(self):
        # Deliberately demonstrates why human review is required.
        self.assertEqual(suggest(self.exercise, 'Train không học tham số')['suggested_total'], 1)

    def test_invalid_quote_rejected(self):
        course = copy.deepcopy(self.course)
        course['exercises'][0]['rubric'][0]['quote'] = 'invented evidence'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            path.write_text(json.dumps(course), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_course(path)

    def test_fingerprint_changes_with_material(self):
        course = json.loads((ROOT / 'data/course.json').read_text(encoding='utf-8'))
        course['passages'][0]['text'] += ' Extra.'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'new.json'
            path.write_text(json.dumps(course), encoding='utf-8')
            self.assertNotEqual(load_course(path)['_fingerprint'], self.course['_fingerprint'])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'db.sqlite3'
        self.con = connect(self.path)
        self.course = load_course(ROOT / 'data/course.json')
        self.ex = self.course['exercises'][0]
        self.id = submit(self.con, 'huni', self.course, self.ex, 'Train học tham số')

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def approve(self):
        review(self.con, self.id, 1, {'train': 1, 'validation': 0, 'test': 0}, 'teacher', 'Explain validation next.')

    def test_pending_not_exported(self):
        self.assertEqual(len(csv_export(self.con, 'huni').splitlines()), 1)

    def test_review_and_progress(self):
        self.approve()
        self.assertEqual(progress(self.con, 'huni')[0]['grade']['total'], 1)
        self.assertEqual(len(csv_export(self.con, 'huni').splitlines()), 2)

    def test_edit_revokes_review(self):
        self.approve()
        revise(self.con, self.id, 2, 'New response')
        self.assertFalse(progress(self.con, 'huni')[0]['reviewed'])
        self.assertEqual(len(csv_export(self.con, 'huni').splitlines()), 1)

    def test_stale_revision_rejected(self):
        self.approve()
        with self.assertRaises(ValueError):
            revise(self.con, self.id, 1, 'Stale response')

    def test_invalid_scores_rejected(self):
        for value in (-1, 2, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                review(self.con, self.id, 1, {'train': value, 'validation': 0, 'test': 0}, 'teacher', 'feedback')

    def test_missing_rubric_rejected(self):
        with self.assertRaises(ValueError):
            review(self.con, self.id, 1, {}, 'teacher', 'feedback')

    def test_blank_reviewer_rejected(self):
        with self.assertRaises(ValueError):
            review(self.con, self.id, 1, {}, '', 'feedback')

    def test_latest_pending_hides_old_grade(self):
        self.approve()
        submit(self.con, 'huni', self.course, self.ex, 'Another attempt')
        self.assertFalse(progress(self.con, 'huni')[0]['reviewed'])

    def test_learner_filter(self):
        self.assertEqual(attempts(self.con, 'other'), [])

    def test_persistence(self):
        self.approve()
        self.con.close()
        self.con = connect(self.path)
        self.assertTrue(progress(self.con, 'huni')[0]['reviewed'])

    def test_csv_formula_escape(self):
        new = submit(self.con, '=CMD()', self.course, self.ex, 'answer')
        review(self.con, new, 1, {'train': 0, 'validation': 0, 'test': 0}, 'teacher', '=IMPORT()')
        exported = csv_export(self.con, '=CMD()')
        self.assertIn("'=CMD()", exported)
        self.assertIn("'=IMPORT()", exported)

    def test_review_uses_saved_rubric(self):
        self.ex['rubric'][0]['max_points'] = 100
        with self.assertRaises(ValueError):
            review(self.con, self.id, 1, {'train': 50, 'validation': 0, 'test': 0}, 'teacher', 'feedback')

    def test_versions_separate(self):
        other = copy.deepcopy(self.course)
        other['_fingerprint'] = 'different'
        submit(self.con, 'huni', other, self.ex, 'answer')
        self.assertEqual(len(progress(self.con, 'huni')), 2)

    def test_event_history_preserves_prior_answer(self):
        revise(self.con, self.id, 1, 'edited')
        events = self.con.execute('SELECT payload FROM events WHERE action=?', ('revised_approval_revoked',)).fetchone()
        self.assertEqual(json.loads(events[0])['previous_answer'], 'Train học tham số')


if __name__ == '__main__':
    unittest.main()

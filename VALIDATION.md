# Validation scope

Verified locally on 2026-11-14: 32 automated tests passed, including a Streamlit AppTest of submit → review → edit → approval revocation, with a temporary database and provider calls mocked. The verification used Python 3.11 and the installed sibling PropertyData-Copilot virtual environment; create a separate environment using requirements.txt for your own run.

The demo contains four self-authored Vietnamese ML passages and three authored exercises. Five retrieval fixtures test four in-domain queries and one unrelated query. Four grading fixtures test lexical concept matching, including a blank answer.

Expected local report: 5/5 retrieval fixtures and 4/4 grading fixtures. These are implementation checks on tiny known examples, not a general retrieval benchmark, semantic grading accuracy, independent teacher agreement, or measured educational benefit.

Automated tests cover literal evidence, invalid quotes, empty answers, phrase boundaries, fingerprint changes, score bounds, stale revisions, saved rubric snapshots, review revocation, learner filtering, persistence, latest-attempt semantics, separate course versions and CSV formula escaping. Provider tests use mocked responses, never a real key or paid request. They cover JSON structure, quote/source validation, abstention and error redaction.

Two explicit limitation tests demonstrate that lexical scoring accepts a negated keyword answer and that a valid quote can accompany a contradictory AI claim. Neither validator establishes semantic correctness.

Run:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 evaluate.py --output reports/my-evaluation-v1.json
```

Reports are local and ignored. The evaluator does not create real learner attempts or human reviews. Live Groq behavior and real learner outcomes require separate evaluation.

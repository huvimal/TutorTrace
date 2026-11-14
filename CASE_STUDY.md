# TutorTrace — Case Study

## Problem
An educational assistant can produce plausible explanations or scores without adequate evidence. A revised student answer can also retain an outdated grade if review state is not tracked explicitly.

## Implementation
TutorTrace is a personal Python/Streamlit prototype with four steps: retrieve course passages, practice authored exercises, review provisional rubric suggestions, and export reviewed progress.

Optional Groq explanations include source IDs and verbatim quotes. The validator checks quote provenance, not whether the source logically supports each claim. Exercises and rubrics are authored rather than generated. Lexical concept matching provides provisional suggestions; reviewers enter scores and feedback explicitly.

SQLite stores answers, rubric snapshots, course fingerprints, revisions and review events. Editing an answer revokes its review. The latest attempt determines progress for each exercise/course fingerprint; an unreviewed resubmission cannot inherit an earlier grade. Reviewed progress exports to CSV with formula escaping.

## Validation evidence
The saved local report `reports/my-evaluation-v1.json` passed all five retrieval fixtures and four lexical grading fixtures. The course contains four self-authored Vietnamese ML passages and three exercises. These small known examples are implementation checks, not a general benchmark.

The verified test suite contains 32 tests, including a Streamlit workflow test of submission, review, editing and approval revocation. Provider requests are mocked. Live Groq explanations, independent teacher agreement and learning outcomes have not been benchmarked. See [VALIDATION.md](VALIDATION.md).

## Deliberate failure demonstrations
A negated answer containing rubric keywords can receive a positive suggestion. A contradictory generated claim can also pass quote validation if its quote is genuine. Tests retain both examples to document the boundary between structural validation and semantic correctness.

## Limits and next steps
This is a local single-user prototype. Learner/reviewer aliases are not authentication, the database is unencrypted, and event records are not tamper-proof. Retrieval is lexical, not embedding-based. No real student data or real-client outcome is claimed.

Further evaluation would require independently authored questions, teacher-reviewed answers, explicit semantic grading criteria, and separate held-out examples before considering educational deployment.

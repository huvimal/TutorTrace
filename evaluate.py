import argparse
import json
from pathlib import Path
from core import load_course, retrieve, suggest


def evaluate():
    root = Path(__file__).resolve().parent
    course = load_course(root / 'data/course.json')
    fixtures = json.loads((root / 'data/fixtures.json').read_text(encoding='utf-8'))
    retrieval = []
    for case in fixtures['retrieval']:
        hits = retrieve(course, case['question'])
        actual = hits[0]['id'] if hits else None
        retrieval.append({**case, 'actual': actual, 'passed': actual == case['expected']})
    exercises = {e['id']: e for e in course['exercises']}
    grading = []
    for case in fixtures['grading']:
        actual = suggest(exercises[case['exercise']], case['answer'])['suggested_total']
        grading.append({**case, 'actual': actual, 'passed': actual == case['expected']})
    return {'mode': 'offline_authored_fixtures', 'course_fingerprint': course['_fingerprint'],
            'retrieval': retrieval, 'grading': grading,
            'summary': {'retrieval_passed': sum(x['passed'] for x in retrieval), 'retrieval_cases': len(retrieval),
                        'grading_passed': sum(x['passed'] for x in grading), 'grading_cases': len(grading)},
            'limits': 'Tiny authored fixtures. Not semantic grading accuracy, learning gains, or independent teacher agreement.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='reports/evaluation.json')
    args = parser.parse_args()
    report = evaluate()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))
    print(f'Report: {output}')
    raise SystemExit(0 if all(c['passed'] for k in ('retrieval', 'grading') for c in report[k]) else 1)

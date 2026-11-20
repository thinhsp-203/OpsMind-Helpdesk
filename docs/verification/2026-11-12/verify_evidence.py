"""Verify this historical evidence bundle locally; does not contact OpsMind."""
import hashlib
import json
import re
from pathlib import Path


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def verify(root):
    provenance = json.loads((root / 'PROVENANCE.json').read_text(encoding='utf-8'))
    for source in provenance['sources']:
        file = (root / source['path']).resolve()
        if not file.is_relative_to(root.resolve()):
            raise ValueError('Invalid source path.')
        if hashlib.sha256(file.read_bytes()).hexdigest() != source['published_sha256']:
            raise ValueError('Source hash mismatch: ' + source['path'])
    cases = read_rows(root / 'cases.jsonl')
    http = read_rows(root / 'http.jsonl')
    final = json.loads((root / 'FINAL.json').read_text(encoding='utf-8'))
    observed = dict(case_rows=len(cases), passed=sum(row['status'] == 'PASS' for row in cases),
                    failed=sum(row['status'] == 'FAIL' for row in cases), http_rows=len(http),
                    http5xx=sum(row['status'] >= 500 for row in http),
                    screenshots=len(list(root.glob('*.png'))))
    if observed != dict(case_rows=46, passed=45, failed=1, http_rows=176, http5xx=0, screenshots=5):
        raise ValueError('Historical counters differ from the recorded result.')
    if provenance['expected'] != observed or final['applicationChecksPassed'] != 45 or final['rawCaseRows'] != 46:
        raise ValueError('Summary and raw rows disagree.')
    failures = [row for row in cases if row['status'] == 'FAIL']
    if len(failures) != 1 or failures[0]['name'] != 'deployed-javascript-matches-reviewed-source':
        raise ValueError('The original failed attempt must remain in the evidence.')
    blob = json.loads((root / 'static-verified.json').read_text(encoding='utf-8'))['detail']
    if blob['expectedGitBlob'] != blob['actualGitBlob'] or blob['actualSha256'] != blob['normalizedLocalSha256']:
        raise ValueError('Missing canonical Git blob explanation for the failed byte comparison.')
    # This is a byte-pinned historical XML file, not an arbitrary XML input API.
    # Count its JUnit records without enabling an XML entity/DTD parser.
    xml_text = (root / 'local-issue12/issue12-tests.xml').read_text(encoding='utf-8')
    if (len(re.findall(r'<testcase(?:\s|/?>)', xml_text)) != 12
            or re.search(r'<(?:failure|error|skipped)(?:\s|/?>)', xml_text)
            or not re.search(r'<testsuite\b[^>]*\btests="12"', xml_text)):
        raise ValueError('Separate local Issue12 XML does not show 12 passing cases.')
    for file in root.rglob('*'):
        if not file.is_file() or file.suffix not in {'.json', '.jsonl', '.xml'}:
            continue
        text = file.read_text(encoding='utf-8')
        if re.search(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b', text):
            raise ValueError('Possible JWT: ' + file.name)
        if re.search(r'"(?:password|old_password|new_password|token|access_token|authorization|cookie)"\s*:\s*"[^"\s]+"', text, re.IGNORECASE):
            raise ValueError('Possible credential field: ' + file.name)
        if re.search(r'[A-Za-z]:[\\/]Users[\\/]', text):
            raise ValueError('Local user home path remains: ' + file.name)
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text):
            raise ValueError('Possible email address: ' + file.name)
    print('PASS: 45 PASS + 1 preserved failed attempt; 176 HTTP rows / 0 HTTP 5xx; source hashes; privacy scan; separate local XML 12 PASS.')
    print('This checks consistency, not origin, password rotation or independent acceptance.')


if __name__ == '__main__':
    verify(Path(__file__).resolve().parent)

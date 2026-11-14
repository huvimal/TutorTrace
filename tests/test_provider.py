import json
import unittest
import urllib.error
from unittest.mock import patch, MagicMock
from provider import validate_reply, explain


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.sources = [{'id': 'S1', 'text': 'Train học tham số.'}]
        self.valid = {'abstain': False, 'claims': [{'text': 'Train học tham số.', 'source_id': 'S1', 'quote': 'Train học tham số.'}]}

    def test_valid_quote(self):
        self.assertEqual(validate_reply(self.valid, self.sources), self.valid)

    def test_invented_quote(self):
        self.valid['claims'][0]['quote'] = 'Test dùng để học.'
        with self.assertRaises(ValueError):
            validate_reply(self.valid, self.sources)

    def test_wrong_source(self):
        self.valid['claims'][0]['source_id'] = 'S9'
        with self.assertRaises(ValueError):
            validate_reply(self.valid, self.sources)

    def test_abstention(self):
        self.assertTrue(validate_reply({'abstain': True, 'claims': []}, self.sources)['abstain'])

    def test_false_claim_known_limitation(self):
        self.valid['claims'][0]['text'] = 'Train không học tham số.'
        # Provenance alone cannot verify entailment.
        self.assertFalse(validate_reply(self.valid, self.sources)['abstain'])

    def test_http_errors_redacted(self):
        error = urllib.error.HTTPError('url', 429, 'secret-key', {}, None)
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(ValueError) as caught:
                explain('secret-key', 'demo', 'Train là gì?', self.sources)
        self.assertNotIn('secret-key', str(caught.exception))

    def test_mock_request(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'choices': [{'message': {'content': json.dumps(self.valid)}}]}).encode()
        with patch('urllib.request.urlopen', return_value=response) as request:
            result = explain('fake', 'demo', 'Train là gì?', self.sources)
        self.assertEqual(len(result['claims']), 1)
        body = json.loads(request.call_args.args[0].data)
        self.assertNotIn('learner', body)

    def test_no_evidence_no_network(self):
        with patch('urllib.request.urlopen') as request:
            self.assertTrue(explain('fake', 'demo', 'Question', [])['abstain'])
            request.assert_not_called()

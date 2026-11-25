"""Problem prompt wiring and replay safety; semantic quality needs a real run."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a'))
import build_exp_a as base
import extraction_v3 as v3


class ProblemPromptChecks(unittest.TestCase):
    def test_problem_prompt_keeps_empty_guard_filter_and_auditable_review(self):
        paper = dict(paper_id='P000001', title='Retrieval',
                     abstract='Existing indexing is too expensive. We use hashing for retrieval.')
        empty = dict(paper_id=paper['paper_id'], **{f: [] for f in base.FACET_NAMES})
        corrected = dict(empty, problem=[dict(concept='Existing indexing is too expensive', evidence_id='A0')],
                         method=[dict(concept='hashing', evidence_id='A1')])
        replies = iter([empty, empty, corrected])
        def generate(messages, seed):
            return json.dumps(next(replies)), dict(usage={})
        with tempfile.TemporaryDirectory() as directory:
            try:
                value, metadata = v3.annotate(paper, '',
                    dict(prompt_version='3.5', seed=42, max_attempts=3,
                         max_new_tokens=2048, dataset_resource_filter=True), {},
                    generate, Path(directory) / 'last_failure.json')
            except ValueError as error:
                self.fail(f'Problem prompt must support the existing extraction pipeline: {error}')
        metadata['prompt_version'] = '3.5'
        self.assertTrue(metadata['validation_passed'])
        self.assertEqual(metadata['attempts_used'], 3)
        self.assertEqual(metadata['request_parameters']['extraction_policy_version'], '3.1')
        self.assertEqual(base.validate_annotation(value, paper, metadata)['problem'],
                         ['Existing indexing is too expensive'])
        self.assertEqual(metadata['postprocessing']['removed'], [])
        tampered = copy.deepcopy(metadata)
        tampered['attempt_scores'][0]['validation_errors'] = []
        with self.assertRaisesRegex(ValueError, 'raw output'):
            base.validate_annotation(value, paper, tampered)

    def test_known_prompt34_replay_does_not_allow_reusing_it_for_prompt35(self):
        fingerprint = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        current = dict(config=dict(extraction_protocol='two_pass_v3', prompt_version='3.4', seed=42),
                       input_hashes={}, generator_version=base.GENERATOR_VERSION,
                       generator_sha256=fingerprint(Path(base.__file__)),
                       protocol_sha256=fingerprint(Path(v3.__file__)))
        saved = dict(current, generator_version='3.5',
                     generator_sha256='079dcce5895a7dfe26de90d668f0b34481612abd44d5aba9e38aefdfd1df137e',
                     protocol_sha256='e538ccc9a66f6683ca4c84c1a7dc794596b209b6d7cccac2280b8e55ff2dcdb1')
        self.assertTrue(base.compatible_provenance(saved, current))
        self.assertFalse(base.compatible_provenance(saved,
            dict(current, config=dict(current['config'], prompt_version='3.5'))))
        self.assertFalse(base.compatible_provenance(dict(saved, protocol_sha256='unknown'), current))


if __name__ == '__main__':
    unittest.main()

"""Verification and no-overwrite guarantees for exported result bundles."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import export_results


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'workspace/results/run'
        self.source.mkdir(parents=True)
        (self.source / 'report.json').write_text('{"ok": true}\n', encoding='utf-8')
        self.manifest = json.dumps({'files': {'report.json': export_results.sha(self.source / 'report.json')}})
        (self.source / 'manifest.json').write_text(self.manifest, encoding='utf-8')
        self.destination = self.root / 'results/run'

    def test_copy_preserves_manifest_and_source(self):
        with patch.object(export_results, 'OWNER', self.root):
            export_results.export_bundle(self.source, self.destination)
        self.assertEqual((self.destination / 'manifest.json').read_text(encoding='utf-8'), self.manifest)
        self.assertEqual((self.destination / 'report.json').read_bytes(), (self.source / 'report.json').read_bytes())
        self.assertTrue((self.destination / 'export_receipt.json').exists())

    def test_corrupt_source_rejected_before_writing(self):
        (self.source / 'report.json').write_text('corrupt', encoding='utf-8')
        with patch.object(export_results, 'OWNER', self.root), self.assertRaises(ValueError):
            export_results.export_bundle(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_never_overwritten(self):
        self.destination.mkdir(parents=True)
        sentinel = self.destination / 'keep.txt'
        sentinel.write_text('keep', encoding='utf-8')
        with patch.object(export_results, 'OWNER', self.root), self.assertRaises(ValueError):
            export_results.export_bundle(self.source, self.destination)
        self.assertEqual(sentinel.read_text(encoding='utf-8'), 'keep')

    def test_manifest_cannot_escape_source(self):
        (self.source / 'manifest.json').write_text(json.dumps({'files': {'../secret': 'bad'}}), encoding='utf-8')
        with patch.object(export_results, 'OWNER', self.root), self.assertRaises(ValueError):
            export_results.export_bundle(self.source, self.destination)
        self.assertFalse(self.destination.exists())


if __name__ == '__main__':
    unittest.main()

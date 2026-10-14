"""Validate real generated colours, aliases and app-format contracts."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cygma_build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class TokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build.generate()
        cls.themes = json.loads(cls.outputs['site/themes.json'])['themes']

    def test_generated_exports_are_current(self):
        for path, contents in self.outputs.items():
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_text(encoding='utf-8'), contents)

    def test_contrast_formula_known_extremes(self):
        self.assertEqual(build.contrast('#000000', '#FFFFFF'), 21)
        self.assertEqual(build.contrast('#AC39F2', '#AC39F2'), 1)
        self.assertLess(build.contrast('#777777', '#FFFFFF'), 4.5)

    def test_report_covers_every_flavour_and_unrounded_threshold(self):
        report = json.loads(self.outputs['reports/contrast.json'])
        self.assertEqual(set(self.themes), {'ember', 'porcelain', 'nocturne'})
        self.assertEqual(report['count'], len(report['pairs']))
        self.assertGreater(report['count'], 500)
        for pair in report['pairs']:
            with self.subTest(pair=pair):
                t = self.themes[pair['theme']]['tokens']
                actual = build.contrast(t[pair['foreground']], t[pair['background']])
                self.assertEqual(pair['ratio'], actual)
                self.assertGreaterEqual(actual, pair['minimum'])

    def test_invalid_pair_fails_build(self):
        themes = copy.deepcopy(self.themes)
        themes['ember']['tokens']['text.primary'] = themes['ember']['tokens']['surface.canvas']
        with self.assertRaises(ValueError):
            build.audit(themes)

    def test_dtcg_aliases_roundtrip_and_reject_cycles(self):
        doc = json.loads(self.outputs['tokens/ember.tokens.json'])
        self.assertEqual(build.resolve(doc), self.themes['ember']['tokens'])
        doc['text']['primary']['$value'] = '{text.secondary}'
        doc['text']['secondary']['$value'] = '{text.primary}'
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            build.resolve(doc)

    def test_dangling_and_transparent_tokens_rejected(self):
        doc = json.loads(self.outputs['tokens/ember.tokens.json'])
        doc['text']['primary']['$value'] = '{base.missing}'
        with self.assertRaises(KeyError):
            build.resolve(doc)
        doc['text']['primary']['$value'] = {'colorSpace': 'srgb', 'components': [0, 0, 0], 'alpha': .5}
        with self.assertRaisesRegex(ValueError, 'opaque'):
            build.resolve(doc)

    def test_native_json_theme_inventory_and_semantic_buttons(self):
        manifest = json.loads(self.outputs['ports/vscode/package.json'])
        self.assertEqual(len(manifest['contributes']['themes']), 3)
        for slug, theme in self.themes.items():
            native = json.loads(self.outputs[f'ports/vscode/themes/cygma-{slug}.json'])
            c = native['colors']
            self.assertEqual(c['editor.background'], theme['tokens']['surface.canvas'])
            self.assertGreaterEqual(build.contrast(c['button.foreground'], c['button.background']), 4.5)
        terminal = json.loads(self.outputs['ports/windows-terminal/cygma.json'])
        self.assertEqual({s['name'] for s in terminal['schemes']}, {'Cygma Ember', 'Cygma Porcelain', 'Cygma Nocturne'})

    def test_native_toml_parses(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest('TOML parser check requires Python 3.11+')
        for name, contents in self.outputs.items():
            if name.endswith('.toml'):
                with self.subTest(name=name):
                    doc = tomllib.loads(contents)
                    self.assertIn('colors', doc)

    def test_tessel_export_matches_semantic_source(self):
        data = json.loads(self.outputs['ports/tessel/cygma.json'])
        for slug, theme in self.themes.items():
            self.assertEqual(data['themes'][slug]['text'], theme['tokens']['text.primary'])
            self.assertEqual(data['themes'][slug]['on_accent'], theme['tokens']['action.onPrimary'])


if __name__ == '__main__':
    unittest.main()

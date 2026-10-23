"""Desktop path selection and transactions use only temporary files."""
import contextlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import manager
from test_manager import _minimal_pe

try:
    import desktop_workflow as workflow
except ImportError:
    workflow = None


@contextlib.contextmanager
def sources(paths):
    specs = {t: dict(s, find=lambda t=t: paths.get(t, [])) for t, s in manager.SPEC.items()}
    with mock.patch.dict(manager.SPEC, specs):
        yield


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(workflow, 'desktop_workflow must implement safe discovery')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def file(self, relative, data=b'x'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def test_discovery_groups_installations_without_selecting_newest(self):
        first = self.file('old/resources/app/out/main.js')
        server = self.file('old/resources/bin/language_server.exe')
        second = self.file('new/resources/app/out/main.js')
        standalone = self.file('manager/resources/bin/language_server.exe')
        with sources({'ide': [first, second], 'manager': [server, standalone]}):
            result = workflow.discover()
        self.assertEqual(len(result.groups['ide']), 2)
        self.assertEqual(len(result.groups['manager']), 1)
        grouped = next(c for c in result.groups['ide'] if c.paths['ide'] == first)
        self.assertEqual(grouped.paths, {'ide': first, 'manager': server})
        alias = self.root / 'alias' / 'language_server.exe'
        alias.parent.mkdir()
        os.link(server, alias)
        with sources({'ide': [first], 'manager': [str(alias), server]}):
            result = workflow.discover()
        self.assertEqual(result.groups['ide'][0].paths, {'ide': first, 'manager': server})
        self.assertEqual(result.groups['manager'], [])
        # A shared main.js does not make two different bundled servers equivalent.
        alias_main = self.root / 'other' / 'resources' / 'app' / 'out' / 'main.js'
        alias_main.parent.mkdir(parents=True)
        os.link(first, alias_main)
        other_server = self.file('other/resources/bin/language_server.exe')
        with sources({'ide': [first, str(alias_main)], 'manager': [server, other_server]}):
            result = workflow.discover()
        self.assertEqual(len(result.groups['ide']), 2)
        self.assertEqual(result.groups['manager'], [])

    def test_discovery_deduplicates_aliases_and_ignores_missing_or_directories(self):
        original = self.file('agy.exe')
        alias = str(self.root / 'alias.exe')
        os.link(original, alias)
        for paths in ([original, original, alias], [str(self.root / 'gone'), original, str(self.root)]):
            with self.subTest(paths=len(paths)), sources({'cli': paths}):
                result = workflow.discover()
                self.assertEqual(len(result.groups['cli']), 1)

    def test_manual_folder_and_source_errors_remain_reviewable(self):
        main = self.file('portable/resources/app/out/main.js')
        with sources({}):
            result = workflow.discover(folder=str(self.root / 'portable'))
        self.assertEqual(result.groups['ide'][0].paths, {'ide': main})
        with sources({}), mock.patch.dict(manager.SPEC['cli'], find=mock.Mock(side_effect=PermissionError)):
            result = workflow.discover()
        self.assertTrue(result.issues)
        self.assertFalse(any(result.groups.values()))


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(workflow, 'desktop_workflow must implement pinned operations')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def binary(self, name='agy.exe'):
        # Verified CLI 1.2.16 x64 bytes and Manager/extension gate in one executable.
        code = bytes.fromhex('4885c00f8498020000807808000f858e020000'
                             'e8284afdff48898424d800000048899c24e000000048898c24e8000000'
                             '80780800743b488b54247048895060')
        path = self.root / name
        path.write_bytes(_minimal_pe(code=code))
        return str(path)

    def test_shared_binary_activate_is_idempotent_and_restore_returns_original(self):
        path = self.binary()
        original = Path(path).read_bytes()
        paths = {'cli': path, 'extension': path}
        for action, expected in [('patch', 'patched'), ('patch', 'patched'), ('restore', 'unpatched')]:
            with self.subTest(action=action, expected=expected):
                result = workflow.execute(action, workflow.inspect(paths))
                self.assertTrue(result['ok'], result['reasons'])
                self.assertEqual({a['state'] for a in result['apps']}, {expected})
        self.assertEqual(Path(path).read_bytes(), original)
        self.assertEqual(Path(path + manager.BAK).read_bytes(), original)
        # A hardlink introduced after patching must reuse the existing clean backup.
        self.assertTrue(workflow.execute('patch', workflow.inspect({'extension': path}))['ok'])
        alias = str(self.root / 'alias.exe')
        os.link(path, alias)
        paths = {'cli': alias, 'extension': path}
        result = workflow.execute('restore', workflow.inspect(paths))
        self.assertTrue(result['ok'], result['reasons'])
        self.assertEqual(Path(alias).read_bytes(), original)
        # Conflicting alias backups must never be picked arbitrarily.
        self.assertTrue(workflow.execute('patch', workflow.inspect({'extension': path}))['ok'])
        Path(alias + manager.BAK).write_bytes(b'conflicting backup')
        before = Path(path).read_bytes()
        result = workflow.execute('restore', workflow.inspect(paths))
        self.assertFalse(result['ok'])
        self.assertEqual(Path(path).read_bytes(), before)

    def test_changed_or_deleted_target_is_never_replaced_by_discovery(self):
        for change in ('rewrite', 'delete', 'replace'):
            with self.subTest(change=change):
                path = self.binary()
                selection = workflow.inspect({'cli': path})
                if change == 'rewrite':
                    with open(path, 'r+b') as stream:
                        stream.seek(0x300)
                        stream.write(b'changed')
                else:
                    os.unlink(path)
                    if change == 'replace':
                        self.binary()
                before = Path(path).read_bytes() if os.path.exists(path) else None
                result = workflow.execute('patch', selection)
                self.assertFalse(result['ok'])
                self.assertFalse(os.path.exists(path + manager.BAK))
                self.assertEqual(Path(path).read_bytes() if os.path.exists(path) else None, before)
        for stage in ('status', 'backup', 'precompare'):
            with self.subTest(stage=stage):
                path = self.binary()
                selection = workflow.inspect({'cli': path})
                original_status = manager.SPEC['cli']['status']
                original_backup = manager.make_backup
                original_equal = manager._files_equal
                replacement = bytearray(Path(path).read_bytes())
                replacement[0x300] = 42
                replaced = False
                def change_then_status(filename):
                    nonlocal replaced
                    if not replaced:
                        replaced = True
                        Path(filename).write_bytes(replacement)
                    return original_status(filename)
                def backup_then_change(filename, **kwargs):
                    saved = original_backup(filename, **kwargs)
                    Path(filename).write_bytes(replacement)
                    return saved
                comparisons = 0
                def change_before_comparison(first, second):
                    nonlocal comparisons
                    if first == path and os.path.basename(second) == 'before':
                        comparisons += 1
                        if comparisons == 2:
                            Path(path).write_bytes(replacement)
                    return original_equal(first, second)
                contexts = {'status': mock.patch.dict(manager.SPEC['cli'], status=change_then_status),
                            'backup': mock.patch('manager.make_backup', side_effect=backup_then_change),
                            'precompare': mock.patch('manager._files_equal', side_effect=change_before_comparison)}
                context = contexts[stage]
                with context:
                    result = workflow.execute('patch', selection)
                self.assertFalse(result['ok'])
                self.assertEqual(Path(path).read_bytes(), bytes(replacement))
                if stage == 'status':
                    self.assertFalse(os.path.exists(path + manager.BAK))

    def test_unsupported_partial_missing_and_write_failures_are_not_success(self):
        path = self.binary()
        bad = self.root / 'main.js'
        bad.write_bytes(b'unsupported')
        for paths in ({}, {'ide': str(bad)}, {'cli': path, 'ide': str(bad)}):
            with self.subTest(targets=list(paths)):
                result = workflow.execute('patch', workflow.inspect(paths))
                self.assertFalse(result['ok'])
                self.assertNotIn(str(self.root), result['report'])
        # A valid gate plus denied write access must produce a failure, not a success.
        denied = self.binary('denied.exe')
        with mock.patch('manager.is_locked', return_value=True):
            result = workflow.execute('patch', workflow.inspect({'cli': denied}))
        self.assertFalse(result['ok'])
        self.assertFalse(os.path.exists(denied + manager.BAK))

    def test_restore_without_verified_backup_leaves_patched_file_untouched(self):
        path = self.binary()
        self.assertTrue(workflow.execute('patch', workflow.inspect({'cli': path}))['ok'])
        Path(path + manager.BAK).write_bytes(b'not a backup')
        before = Path(path).read_bytes()
        result = workflow.execute('restore', workflow.inspect({'cli': path}))
        self.assertFalse(result['ok'])
        self.assertEqual(Path(path).read_bytes(), before)

    def test_activate_button_runs_discovery_and_verified_operation_without_account_reads(self):
        try:
            import tkinter as tk
            from desktop import Desktop
            root = tk.Tk()
        except ImportError:
            self.skipTest('Tk not available')
        except tk.TclError:
            self.skipTest('Tk/display not available')
        self.addCleanup(root.destroy)
        root.withdraw()
        path = self.binary()
        before = Path(path).read_bytes()
        with sources({'cli': [path]}), \
                mock.patch('manager.cred_read', side_effect=AssertionError('No account reads')), \
                mock.patch('manager.ide_read', side_effect=AssertionError('No account reads')):
            app = Desktop(root)
            root.update_idletasks()
            self.assertEqual(Path(path).read_bytes(), before)
            app.activate.invoke()
            deadline = time.monotonic() + 10
            while not app.apps and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            self.assertEqual([a['state'] for a in app.apps], ['patched'])
            self.assertEqual(app.heading.get(), 'Active')
            app.start('restore')
            while app.heading.get() != 'Originals restored' and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            self.assertEqual(Path(path).read_bytes(), before)
            self.assertEqual(app.heading.get(), 'Originals restored')


if __name__ == '__main__':
    unittest.main()

"""Fresh desktop discovery and pinned operations; no GUI or account access."""
# Desktop edition and modifications copyright (c) 2026 Abdallah22s; see LICENSE.
from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import hashlib
import io
import os
from pathlib import Path

import manager
from desktop_support import diagnostic_reasons, error_report

NAMES = {'cli': 'Command-line tool', 'manager': 'Antigravity Manager',
         'ide': 'Antigravity IDE', 'extension': 'Antigravity Extension'}
GROUP_NAMES = {'ide': 'IDE installation', 'manager': 'Manager installation',
               'cli': 'Command-line tool', 'extension': 'Extension binary'}


@dataclass
class Candidate:
    paths: dict
    source: str


@dataclass
class Discovery:
    groups: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)


@dataclass
class Selection:
    paths: dict
    stamps: dict
    apps: list
    issues: list = field(default_factory=list)


def _physical(path):
    stat = os.stat(path)
    return (stat.st_dev, stat.st_ino) if stat.st_ino else os.path.normcase(os.path.realpath(path))


def _root(path, target):
    path = Path(path)
    # Both layouts are bounded, known installation suffixes, not recursive searches.
    suffix = ('resources', 'app', 'out', 'main.js') if target == 'ide' else ('resources', 'bin', path.name)
    parts = tuple(p.lower() for p in path.parts)
    if parts[-len(suffix):] == tuple(p.lower() for p in suffix):
        root = path.parents[len(suffix) - 1]
        return os.path.normcase(str(root))
    return os.path.normcase(str(path.parent))


def _folder_paths(folder):
    root = Path(folder).expanduser().resolve()
    out = {t: [] for t in manager.TARGETS}
    for base in (root, root / 'Contents'):
        for name in ('language_server.exe', 'language_server'):
            out['manager'].append(str(base / 'resources' / 'bin' / name))
            out['manager'].append(str(base / 'Resources' / 'bin' / name))
        out['ide'].append(str(base / 'resources' / 'app' / 'out' / 'main.js'))
        out['ide'].append(str(base / 'Resources' / 'app' / 'out' / 'main.js'))
    for name in ('agy.exe', 'agy'):
        out['cli'].extend([str(root / name), str(root / 'bin' / name)])
    return out


def discover(manual=None, folder=None):
    """Return all distinct choices, never choose one by timestamp or source rank.

    manual maps component IDs to explicitly selected files. A folder contributes
    only known relative paths. All filesystem and registry reads are fresh.
    """
    manager._reg_install_dirs.cache_clear()
    manager._roots.cache_clear()
    result = Discovery({t: [] for t in manager.TARGETS})
    candidates = {t: [] for t in manager.TARGETS}
    extras = _folder_paths(folder) if folder else {}
    for target in manager.TARGETS:
        try:
            paths = [(p, 'Automatic discovery (known locations / PATH / registry)')
                     for p in manager.SPEC[target]['find']()]
        except Exception:
            result.issues.append('Some installation locations could not be inspected. Choose a location manually or retry.')
            paths = []
        paths.extend((p, 'Selected folder') for p in extras.get(target, []))
        if manual and manual.get(target):
            paths.append((manual[target], 'Selected file'))
        seen = set()
        for path, source in paths:
            try:
                if not os.path.isfile(path):
                    continue
                physical = _physical(path)
                # Retain server aliases until installation relationships are known.
                if physical in seen and target not in ('manager', 'ide'):
                    continue
                seen.add(physical)
                path = os.path.realpath(os.path.abspath(path))
                candidates[target].append(Candidate({target: path}, source))
            except OSError:
                result.issues.append('Some installation locations could not be inspected. Choose a location manually or retry.')

    # Colocated IDE and server belong together; standalone Managers remain independent.
    grouped_identities = set()
    for ide in candidates['ide']:
        root = _root(ide.paths['ide'], 'ide')
        servers = [s for s in candidates['manager'] if _root(s.paths['manager'], 'manager') == root]
        for server in servers or [None]:
            paths = dict(ide.paths)
            if server:
                paths.update(server.paths)
            identity = tuple((t, _physical(p)) for t, p in sorted(paths.items()))
            if identity not in grouped_identities:
                grouped_identities.add(identity)
                result.groups['ide'].append(Candidate(paths, ide.source))
    attached = {_physical(p) for c in result.groups['ide'] for t, p in c.paths.items() if t == 'manager'}
    for candidate in candidates['manager']:
        identity = _physical(candidate.paths['manager'])
        if identity not in attached:
            result.groups['manager'].append(candidate)
            attached.add(identity)
    result.groups['cli'] = candidates['cli']
    result.groups['extension'] = candidates['extension']
    result.issues = list(dict.fromkeys(result.issues))
    return result


def _stamp(path):
    with open(path, 'rb') as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    def metadata(stat):
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
    if metadata(before) != metadata(after) or metadata(after) != metadata(os.stat(path)):
        raise OSError('target changed during inspection')
    return metadata(after), digest.digest()


def _app(target, path):
    try:
        state = manager.SPEC[target]['status'](path)[0]
    except Exception:
        state = 'error'
    return dict(target=target, name=NAMES[target], path=path, state=state)


def inspect(paths):
    """Pin physical files and full contents; validation failures remain visible."""
    canonical, stamps, apps, physical_paths, aliases, issues = {}, {}, [], {}, {}, []
    for target, path in paths.items():
        try:
            aliases.setdefault(_physical(path), []).append(os.path.realpath(os.path.abspath(path)))
        except OSError:
            pass
    conflicts = set()
    for physical, names in aliases.items():
        backed = list(dict.fromkeys(p for p in names if os.path.isfile(p + manager.BAK)))
        if len(backed) > 1 and any(not manager._files_equal(backed[0] + manager.BAK, p + manager.BAK) for p in backed[1:]):
            conflicts.add(physical)
            issues.append('Existing backups for aliases disagree. Restore a verified original before retrying.')
        physical_paths[physical] = backed[0] if backed else names[0]
    for target in manager.TARGETS:
        if not paths.get(target):
            continue
        path = os.path.realpath(os.path.abspath(paths[target]))
        try:
            # Hardlink aliases must share the exact same backup path across gates.
            physical = _physical(path)
            if physical in conflicts:
                raise OSError('conflicting alias backups')
            path = physical_paths.setdefault(physical, path)
            before = _stamp(path)
            app = _app(target, path)
            after = _stamp(path)
            if before != after:
                raise OSError('target changed during inspection')
            stamps[target] = after
        except OSError:
            app = dict(target=target, name=NAMES[target], path=path, state='error')
        canonical[target] = path
        apps.append(app)
    return Selection(canonical, stamps, apps, issues)


def execute(action, selection):
    """Operate only on selected, unchanged files and report each verified result.

    Transactions are per component, matching the CLI. A failed component never
    turns a partially completed operation into an overall success.
    """
    if action not in ('patch', 'restore'):
        raise ValueError('Unknown operation')
    desired = 'patched' if action == 'patch' else 'unpatched'
    source = 'unpatched' if action == 'patch' else 'patched'
    expected = dict(selection.stamps)
    reasons = list(selection.issues)
    succeeded = bool(selection.paths) and not selection.issues
    if not selection.paths:
        reasons.append('No components were selected. Choose an installation location.')
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        for app in selection.apps:
            target, path = app['target'], app['path']
            try:
                if target not in expected or _stamp(path) != expected[target]:
                    raise OSError('target changed since selection')
                state = manager.SPEC[target]['status'](path)[0]
                def guard(filename):
                    if filename != path or _stamp(filename) != expected[target]:
                        raise OSError('target changed since selection')
                guard(path)
                if state == desired:
                    continue
                if state != source:
                    succeeded = False
                    reasons.append('The installed build does not match a supported signature.')
                    continue
                rc = manager.run(action, [target], {target: path}, guard=guard)
                final = manager.SPEC[target]['status'](path)[0]
                if rc or final != desired:
                    succeeded = False
                    reasons.append('A component could not be verified after the operation. Review its result before retrying.')
                    continue
                # Our verified write may affect another gate in the same binary.
                updated = _stamp(path)
                for other, other_path in selection.paths.items():
                    if other_path == path:
                        expected[other] = updated
            except OSError:
                succeeded = False
                reasons.append('The selected file changed or became inaccessible. Retry Activate to select and inspect it again.')
            except Exception:
                succeeded = False
                reasons.append('A component could not be verified after the operation. Review its result before retrying.')
    reasons.extend(diagnostic_reasons(output.getvalue()))
    output.close()
    apps = [_app(t, p) for t, p in selection.paths.items()]
    succeeded = succeeded and all(a['state'] == desired for a in apps)
    reasons = list(dict.fromkeys(reasons))
    return dict(ok=succeeded, apps=apps, reasons=reasons,
                report=error_report(action, apps, reasons) if not succeeded else '')

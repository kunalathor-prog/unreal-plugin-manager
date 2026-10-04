"""Lossless line-oriented Unreal INI merging and reversible multi-file writes."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from app.core.project_manager import ProjectManager


@dataclass(frozen=True)
class ConfigChange:
    relative: str
    before: bytes | None
    after: bytes | None


@dataclass(frozen=True)
class ConfigPlan:
    target: Path
    changes: tuple[ConfigChange, ...]
    skipped: tuple[str, ...] = ()

    def preview(self) -> str:
        parts = []
        for change in self.changes:
            before = decode_ini(change.before)[0] if change.before is not None else ''
            after = decode_ini(change.after)[0] if change.after is not None else ''
            parts.append(''.join(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True),
                fromfile=f'Target/Config/{change.relative}',
                tofile=f'Merged/Config/{change.relative}')))
        if self.skipped:
            parts.append('\nNon-INI files not copied:\n' + '\n'.join(self.skipped))
        return '\n'.join(parts)


def decode_ini(data: bytes) -> tuple[str, str]:
    encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig' if data.startswith(b'\xef\xbb\xbf') else 'utf-8'
    text = data.decode(encoding)
    if '\x00' in text:
        raise ValueError('Unsupported INI encoding or binary content.')
    return text, encoding


def parse_ini(text: str):
    lines = text.splitlines(keepends=True)
    section = None
    groups, labels, last, identities = {}, {}, {}, {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        header = re.fullmatch(r'\[([^\]]+)\]\s*(?:;.*)?', stripped)
        if header:
            section = header[1].casefold()
            labels.setdefault(section, header[1])
        elif stripped and not stripped.startswith((';', '#')):
            if section is None or '=' not in stripped or stripped.endswith('\\'):
                raise ValueError(f'Unsupported INI syntax at line {index + 1}; no files were changed.')
            key = stripped.split('=', 1)[0].strip().lstrip('+-.!').strip().casefold()
            if not key:
                raise ValueError(f'Empty INI key at line {index + 1}.')
            identity = (section, key)
            groups.setdefault(identity, []).append(line)
            identities[index] = identity
        if section is not None:
            last[section] = index
    return lines, groups, labels, last, identities


def merge_ini(target: bytes, source: bytes) -> bytes:
    """Source replaces each matching key's complete ordered operator group."""
    target_text, encoding = decode_ini(target)
    source_text, _ = decode_ini(source)
    lines, target_groups, target_labels, last, identities = parse_ini(target_text)
    source_lines, groups, labels, _, _ = parse_ini(source_text)
    if not lines:
        return source
    newline = '\r\n' if '\r\n' in target_text else '\n'
    emitted = set()
    ending_sections = {end: section for section, end in last.items()}
    output = []

    def add_line(line):
        if output and not output[-1].endswith(('\n', '\r')):
            output[-1] += newline
        output.append(line.rstrip('\r\n') + newline)

    for index, line in enumerate(lines):
        identity = identities.get(index)
        if identity in groups:
            if identity not in emitted:
                for replacement in groups[identity]:
                    add_line(replacement)
                emitted.add(identity)
        else:
            output.append(line)
        section = ending_sections.get(index)
        if section is not None:
            for identity, replacements in groups.items():
                if identity[0] == section and identity not in target_groups:
                    for replacement in replacements:
                        add_line(replacement)
                    emitted.add(identity)
    # Copy new source sections including comments and repeated section blocks.
    section = None
    for line in source_lines:
        header = re.fullmatch(r'\[([^\]]+)\]\s*(?:;.*)?', line.strip())
        if header:
            section = header[1].casefold()
        if section is not None and section not in target_labels:
            add_line(line)
    merged = ''.join(output)
    return target if merged == target_text else merged.encode(encoding)


def safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in relative or ':' in relative or rel.suffix.lower() != '.ini':
        raise ValueError(f'Invalid Config path: {relative}')
    path = root / rel
    for part in (root, *path.parents, path):
        if part.is_symlink():
            raise ValueError(f'Symbolic links are not supported: {part}')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Config path escapes the project.')
    return path


def read_optional(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


class ConfigService:
    @staticmethod
    def plan(source_project: Path, target_project: Path) -> ConfigPlan:
        ProjectManager.load_descriptor(source_project)
        ProjectManager.load_descriptor(target_project)
        source = source_project.resolve().parent / 'Config'
        target = target_project.resolve().parent / 'Config'
        if source == target or source in target.parents or target in source.parents:
            raise ValueError('Select a different source project.')
        if not source.is_dir() or source.is_symlink():
            raise ValueError('Source project must have a regular Config directory.')
        changes, skipped, seen = [], [], set()
        for folder, dirs, files in os.walk(source):
            for name in sorted(dirs + files):
                if (Path(folder) / name).is_symlink():
                    raise ValueError('Config contains symbolic links; resolve them before copying.')
            for name in sorted(files):
                path = Path(folder) / name
                relative = path.relative_to(source).as_posix()
                if path.suffix.lower() != '.ini':
                    skipped.append(relative)
                    continue
                if relative.casefold() in seen:
                    raise ValueError(f'Case-colliding Config filenames: {relative}')
                seen.add(relative.casefold())
                destination = safe_path(target, relative)
                before = read_optional(destination)
                data = path.read_bytes()
                parse_ini(decode_ini(data)[0])
                after = merge_ini(before, data) if before is not None else data
                if before != after:
                    changes.append(ConfigChange(relative, before, after))
        return ConfigPlan(target, tuple(changes), tuple(skipped))

    @staticmethod
    def apply(plan: ConfigPlan) -> Path:
        if not plan.changes:
            raise ValueError('No Config changes to apply.')
        for change in plan.changes:
            if read_optional(safe_path(plan.target, change.relative)) != change.before:
                raise ValueError(f'{change.relative} changed since preview. Preview again.')
        backup_dir = plan.target.parent / '.pipeline-config-backups'
        if backup_dir.is_symlink():
            raise ValueError('Backup directory cannot be a symbolic link.')
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backup = backup_dir / f'{stamp}-{uuid.uuid4().hex[:8]}.json'
        record = {'version': 1, 'target': str(plan.target.resolve()), 'files': [
            {'path': c.relative,
             'before': base64.b64encode(c.before).decode('ascii') if c.before is not None else None,
             'after_sha256': hashlib.sha256(c.after).hexdigest() if c.after is not None else None}
            for c in plan.changes]}
        ProjectManager.atomic_write(backup, json.dumps(record, indent=2).encode('utf-8'))
        written = []
        try:
            for change in plan.changes:
                path = safe_path(plan.target, change.relative)
                if read_optional(path) != change.before:
                    raise ValueError(f'{change.relative} changed during apply.')
                path.parent.mkdir(parents=True, exist_ok=True)
                if change.after is None:
                    path.unlink()
                else:
                    ProjectManager.atomic_write(path, change.after)
                written.append(change)
        except Exception as exc:
            failures = []
            for change in reversed(written):
                try:
                    path = safe_path(plan.target, change.relative)
                    if change.before is None:
                        path.unlink(missing_ok=True)
                    else:
                        ProjectManager.atomic_write(path, change.before)
                except Exception as rollback_error:
                    failures.append(str(rollback_error))
            detail = f' Rollback errors: {failures}.' if failures else ' Completed writes were rolled back.'
            raise RuntimeError(f'{exc}.{detail} Backup: {backup}') from exc
        return backup

    @staticmethod
    def restore_plan(target_project: Path, backup: Path) -> ConfigPlan:
        ProjectManager.load_descriptor(target_project)
        target = target_project.resolve().parent / 'Config'
        record = json.loads(backup.read_text(encoding='utf-8'))
        if record.get('version') != 1 or record.get('target') != str(target.resolve()):
            raise ValueError('Backup belongs to another project or has an unsupported format.')
        changes, seen = [], set()
        for entry in record['files']:
            relative = entry['path']
            if relative.casefold() in seen:
                raise ValueError('Duplicate backup paths.')
            seen.add(relative.casefold())
            current = read_optional(safe_path(target, relative))
            digest = hashlib.sha256(current).hexdigest() if current is not None else None
            if digest != entry['after_sha256']:
                raise ValueError(f'{relative} changed after this backup was made; automatic restore refused.')
            original = base64.b64decode(entry['before'], validate=True) if entry['before'] is not None else None
            if original is not None:
                parse_ini(decode_ini(original)[0])
            changes.append(ConfigChange(relative, current, original))
        return ConfigPlan(target, tuple(changes))

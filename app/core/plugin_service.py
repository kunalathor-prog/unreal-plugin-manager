"""Descriptor-level plugin state and recoverable filesystem operations."""
from __future__ import annotations

import json
import shutil
import tempfile
from copy import deepcopy
from pathlib import Path

from app.core.project_manager import ProjectManager


def enabled_state(meta: dict, origin: str, override: bool | None, disable_engine_defaults: bool = False) -> bool:
    if override is not None:
        return override
    # External plugins are available for import, not installed in the project yet.
    if origin == "Custom" or (origin == "Engine" and disable_engine_defaults):
        return False
    return meta.get("EnabledByDefault", origin == "Project") is True


class PluginService:
    @staticmethod
    def validate_copy(source: Path, destination: Path) -> None:
        src, dst = source.resolve(), destination.resolve()
        if src == dst or src in dst.parents or dst in src.parents:
            raise ValueError("Source and destination plugin folders must not overlap.")
        if destination.is_symlink():
            raise ValueError("Cannot replace a symbolic-link destination.")
        descriptors = list(source.glob("*.uplugin"))
        if len(descriptors) != 1:
            raise ValueError("Select a folder containing exactly one .uplugin descriptor.")
        data = json.loads(descriptors[0].read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Plugin descriptor must be a JSON object.")

    @staticmethod
    def updated_descriptor(descriptor: dict, selections: dict[str, bool], plugins: dict) -> dict:
        result = deepcopy(descriptor)
        entries = {entry["Name"]: entry for entry in result.get("Plugins", [])}
        for name, enabled in selections.items():
            # Preserve inherited defaults unless the user actually changes the state.
            if enabled == plugins[name]["enabled"]:
                continue
            entries[name] = {**entries.get(name, {}), "Name": name, "Enabled": enabled}
        result["Plugins"] = sorted(entries.values(), key=lambda entry: entry["Name"].lower())
        return result

    @classmethod
    def transact(cls, copies: list[tuple[Path, Path]], commit=lambda: None) -> None:
        """Stage every copy before replacing anything; roll back if commit fails."""
        staged = []
        committed = False
        try:
            destinations = set()
            for source, destination in copies:
                cls.validate_copy(source, destination)
                resolved = destination.resolve()
                if resolved in destinations:
                    raise ValueError(f"Multiple plugins target the same folder: {destination}")
                destinations.add(resolved)
                destination.parent.mkdir(parents=True, exist_ok=True)
                work = Path(tempfile.mkdtemp(prefix=".plugin-import-", dir=destination.parent))
                item = {"destination": destination, "work": work, "old": False, "new": False}
                staged.append(item)
                shutil.copytree(source, work / "new")
            for item in staged:
                destination, work = item["destination"], item["work"]
                if destination.exists():
                    destination.rename(work / "old")
                    item["old"] = True
                (work / "new").rename(destination)
                item["new"] = True
            commit()
            committed = True
        except Exception:
            for item in reversed(staged):
                destination, work = item["destination"], item["work"]
                if item["new"]:
                    shutil.rmtree(destination)
                if item["old"]:
                    (work / "old").rename(destination)
                    item["old"] = False
            raise
        finally:
            for item in staged:
                # Leave recoverable originals on disk if rollback itself fails.
                if committed or not item["old"]:
                    shutil.rmtree(item["work"], ignore_errors=True)

    @classmethod
    def apply(cls, project: Path, selections: dict[str, bool], plugins: dict, expected: bytes) -> None:
        if project.read_bytes() != expected:
            raise ValueError("Project changed since the scan. Rescan before applying.")
        descriptor = ProjectManager.load_descriptor(project)
        updated = cls.updated_descriptor(descriptor, selections, plugins)
        copies = [(info["plugin_dir"], project.parent / "Plugins" / info["plugin_dir"].name)
                  for name, info in plugins.items() if selections[name] and info["origin"] == "Custom"]

        def commit():
            if project.read_bytes() != expected:
                raise ValueError("Project changed during import. Rescan before applying.")
            ProjectManager.save_descriptor(project, updated)

        cls.transact(copies, commit)

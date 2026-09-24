"""Persistence adapter for investigation/version metadata.

It reuses the existing chat metadata JSON. No parallel folder hierarchy is
created and no artifact is duplicated.
"""
from __future__ import annotations

import json
import os
import shutil
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from security_utils import validate_component, safe_child_path
from investigation_model import InvestigationVersion


def _meta_path(chats_dir: str, chat_id: str) -> str:
    chat_id = validate_component(chat_id, "chat_id")
    return safe_child_path(
        safe_child_path(chats_dir, chat_id),
        "conversacion_metadata.json",
    )


def _load(chats_dir: str, chat_id: str) -> Dict[str, Any]:
    path = _meta_path(chats_dir, chat_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chat metadata not found: {chat_id}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(chats_dir: str, chat_id: str, meta: Dict[str, Any]) -> None:
    path = _meta_path(chats_dir, chat_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_response(meta: Dict[str, Any], folder: str) -> Optional[Dict[str, Any]]:
    for response in meta.get("responses", []):
        if response.get("folder") == folder:
            return response
    return None




_ARTIFACT_ROOTS = {
    "documentos": ("entregables", "documentos"),
    "visualizador_interactivo": ("entregables", "visualizador_interactivo"),
    "imagenes": ("entregables", "imagenes"),
    "codigo_graficos": ("entregables", "codigo_graficos"),
    "proceso_agentes": ("proceso_agentes",),
}
_ARTIFACT_TYPE_BY_EXTENSION = {
    ".md": "md", ".html": "html", ".docx": "docx", ".doc": "doc",
    ".png": "imagenes", ".jpg": "imagenes", ".jpeg": "imagenes", ".svg": "imagenes",
    ".py": "codigo", ".js": "codigo", ".css": "codigo",
}


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_manifest(chats_dir: str, chat_id: str, folder: str, *, version_id: Optional[str] = None, previous_manifest: Optional[Dict[str, Any]] = None, changed_files: Optional[list[str]] = None) -> Dict[str, Any]:
    """Inspect the existing response folder and describe actual artifacts on disk."""
    response_path = safe_child_path(safe_child_path(chats_dir, validate_component(chat_id, "chat_id")), validate_component(folder, "folder"))
    artifacts: list[Dict[str, Any]] = []
    previous = {str(a.get("path")): a for a in (previous_manifest or {}).get("artifacts", [])}
    changed = {str(p).replace(os.sep, "/") for p in (changed_files or [])}
    source_md_sha256 = None
    for root_type, parts in _ARTIFACT_ROOTS.items():
        root = response_path
        for part in parts:
            root = os.path.join(root, part)
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in sorted(filenames):
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, response_path).replace(os.sep, "/")
                stat = os.stat(path)
                artifacts.append({
                    "artifact_id": f"artifact-{hashlib.sha256(rel.encode('utf-8')).hexdigest()[:16]}",
                    "type": _ARTIFACT_TYPE_BY_EXTENSION.get(os.path.splitext(filename)[1].lower(), root_type),
                    "path": rel,
                    "filename": filename,
                    "size": stat.st_size,
                    "sha256": _sha256_file(path),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "status": "current",
                    "version_id": version_id,
                    "source_md_sha256": source_md_sha256,
                    "derived_from": version_id,
                })
    md_items = [a for a in artifacts if a.get("type") == "md"]
    if md_items:
        source_md_sha256 = md_items[0].get("sha256")
    for item in artifacts:
        item["source_md_sha256"] = source_md_sha256
        rel = str(item["path"])
        old = previous.get(rel)
        if item.get("type") == "md":
            item["status"] = "current"
        elif old and old.get("sha256") == item.get("sha256") and old.get("source_md_sha256") == source_md_sha256:
            item["status"] = old.get("status", "current")
        elif item.get("type") in {"html", "docx", "doc", "simulador", "imagenes", "codigo"}:
            # Derived artifacts become stale whenever their recorded source
            # Markdown digest no longer matches the current canonical source.
            item["status"] = (
                "stale"
                if old and old.get("source_md_sha256") != source_md_sha256
                else "current"
            )
        else:
            item["status"] = "current"
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "version_id": version_id, "source_md_sha256": source_md_sha256, "artifacts": artifacts}


def refresh_artifact_manifest(chats_dir: str, chat_id: str, folder: str, *, version_id: Optional[str] = None, changed_files: Optional[list[str]] = None) -> Dict[str, Any]:
    """Persist a fresh manifest in the existing response metadata."""
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    previous = response.get("artifact_manifest") or {}
    manifest = build_artifact_manifest(chats_dir, chat_id, folder, version_id=version_id or response.get("version_id"), previous_manifest=previous, changed_files=changed_files)
    response["artifact_manifest"] = manifest
    response["artifact_manifest_version_id"] = manifest["version_id"]
    _save(chats_dir, chat_id, meta)
    return manifest


def _version_snapshot_root(chats_dir: str, chat_id: str, folder: str, version_id: str) -> str:
    response_path = safe_child_path(
        safe_child_path(chats_dir, validate_component(chat_id, "chat_id")),
        validate_component(folder, "folder"),
    )
    validate_component(version_id, "version_id")
    return safe_child_path(response_path, "version_snapshots", str(version_id))


def snapshot_version_artifacts(
    chats_dir: str,
    chat_id: str,
    folder: str,
    version_id: str,
) -> Dict[str, Any]:
    """Create an immutable physical snapshot of managed artifacts for a version."""
    response_path = safe_child_path(
        safe_child_path(chats_dir, validate_component(chat_id, "chat_id")),
        validate_component(folder, "folder"),
    )
    snapshot_root = _version_snapshot_root(chats_dir, chat_id, folder, version_id)
    if os.path.exists(snapshot_root):
        raise FileExistsError(f"Snapshot already exists for version: {version_id}")

    os.makedirs(snapshot_root, exist_ok=False)
    entries = []
    try:
        for root_type, parts in _ARTIFACT_ROOTS.items():
            source_root = response_path
            for part in parts:
                source_root = os.path.join(source_root, part)
            if not os.path.isdir(source_root):
                continue
            for dirpath, _, filenames in os.walk(source_root):
                for filename in filenames:
                    source = os.path.join(dirpath, filename)
                    rel = os.path.relpath(source, response_path).replace(os.sep, "/")
                    target = safe_child_path(snapshot_root, *rel.split("/"))
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(source, target)
                    entries.append({
                        "path": rel,
                        "sha256": _sha256_file(target),
                        "size": os.path.getsize(target),
                        "type": _ARTIFACT_TYPE_BY_EXTENSION.get(
                            os.path.splitext(filename)[1].lower(), root_type
                        ),
                    })
    except Exception:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        raise

    snapshot = {
        "version_id": str(version_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": "version_snapshots/" + str(version_id),
        "artifacts": sorted(entries, key=lambda item: item["path"]),
    }
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    response.setdefault("version_snapshots", {})[str(version_id)] = snapshot
    for item in response.get("version_history", []):
        if item.get("version_id") == str(version_id):
            item["snapshot_available"] = True
            item["snapshot_artifact_count"] = len(entries)
    _save(chats_dir, chat_id, meta)
    return snapshot


def get_version_snapshot(
    chats_dir: str,
    chat_id: str,
    folder: str,
    version_id: str,
) -> Optional[Dict[str, Any]]:
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    snapshot = (response.get("version_snapshots") or {}).get(str(version_id))
    if snapshot:
        return dict(snapshot)
    return None


def restore_version_snapshot(
    chats_dir: str,
    chat_id: str,
    folder: str,
    version_id: str,
) -> Dict[str, Any]:
    """Restore a snapshot into the live managed artifact roots."""
    snapshot = get_version_snapshot(chats_dir, chat_id, folder, version_id)
    if snapshot is None:
        raise FileNotFoundError(f"No physical snapshot exists for version: {version_id}")

    response_path = safe_child_path(
        safe_child_path(chats_dir, validate_component(chat_id, "chat_id")),
        validate_component(folder, "folder"),
    )
    snapshot_root = _version_snapshot_root(chats_dir, chat_id, folder, version_id)
    expected = {str(item["path"]) for item in snapshot.get("artifacts", [])}

    # Remove managed files absent from the selected snapshot.
    for root_type, parts in _ARTIFACT_ROOTS.items():
        root = response_path
        for part in parts:
            root = os.path.join(root, part)
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root, topdown=False):
            for filename in filenames:
                source = os.path.join(dirpath, filename)
                rel = os.path.relpath(source, response_path).replace(os.sep, "/")
                if rel not in expected:
                    os.remove(source)
            for dirname in _:
                pass

    restored = []
    for item in snapshot.get("artifacts", []):
        rel = str(item["path"])
        source = safe_child_path(snapshot_root, *rel.split("/"))
        target = safe_child_path(response_path, *rel.split("/"))
        if not os.path.isfile(source):
            raise FileNotFoundError(f"Snapshot artifact missing: {rel}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)
        digest = _sha256_file(target)
        if digest != item.get("sha256"):
            raise IOError(f"Snapshot integrity check failed: {rel}")
        restored.append(rel)

    return {
        "version_id": str(version_id),
        "restored_files": restored,
        "count": len(restored),
        "snapshot": snapshot,
    }


def set_evaluation_profile(
    chats_dir: str,
    chat_id: str,
    folder: str,
    profile: Dict[str, int],
) -> Dict[str, Any]:
    """Persist the current target profile on the existing investigation response."""
    allowed = {
        "mathematics", "depth", "explanation", "visualization",
        "interactivity", "images", "code", "structure",
    }
    normalized = {}
    for key, value in dict(profile or {}).items():
        if key not in allowed:
            raise ValueError(f"Unknown evaluation dimension: {key}")
        value = int(value)
        if not 0 <= value <= 100:
            raise ValueError(f"{key} must be between 0 and 100")
        normalized[key] = value
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    response["evaluation_profile"] = normalized
    response["evaluation_profile_source"] = "user_current_target"
    _save(chats_dir, chat_id, meta)
    return normalized


def get_evaluation_profile(
    chats_dir: str,
    chat_id: str,
    folder: str,
) -> Dict[str, int]:
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    return dict(response.get("evaluation_profile") or {})


def register_version(
    chats_dir: str,
    chat_id: str,
    folder: str,
    *,
    prompt: str,
    title: str,
    source: str = "pipeline",
    parent_version_id: Optional[str] = None,
    commands: Optional[list[str]] = None,
    references: Optional[list[str]] = None,
    artifact_types: Optional[list[str]] = None,
    status: str = "succeeded",
    strategy_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")

    investigation_id = response.get(
        "investigation_id",
        f"{chat_id}/{folder}",
    )
    version = InvestigationVersion.create(
        investigation_id=investigation_id,
        prompt=prompt,
        title=title,
        parent_version_id=parent_version_id or response.get("version_id"),
        response_folder=folder,
        source=source,
        commands=commands,
        references=references,
        artifact_types=artifact_types or response.get("artifact_types", []),
        status=status,
        strategy_context=strategy_context or {},
    )
    response["version_id"] = version.version_id
    response["parent_version_id"] = version.parent_version_id
    response["version_source"] = version.source
    response.setdefault("version_history", []).append(version.to_dict())
    response.setdefault("commands", []).extend(commands or [])
    response.setdefault("references", []).extend(references or [])
    _save(chats_dir, chat_id, meta)
    snapshot_version_artifacts(chats_dir, chat_id, folder, version.version_id)
    return version.to_dict()



def get_version(chats_dir, chat_id, folder, version_id):
    """Return one logical version from the existing response metadata."""
    versions = list_versions(chats_dir, chat_id, folder)
    for version in versions:
        if version.get("version_id") == str(version_id):
            return version
    return None


def navigate_versions(chats_dir, chat_id, folder, version_id):
    """Return previous/current/next positions without mutating history."""
    versions = list_versions(chats_dir, chat_id, folder)
    if not versions:
        raise ValueError("La investigación no contiene versiones")
    ids = [v.get("version_id") for v in versions]
    try:
        idx = ids.index(str(version_id))
    except ValueError:
        raise ValueError("Versión no encontrada")
    return {
        "current": versions[idx],
        "index": idx,
        "count": len(versions),
        "previous": versions[idx - 1] if idx > 0 else None,
        "next": versions[idx + 1] if idx + 1 < len(versions) else None,
    }
def list_versions(chats_dir: str, chat_id: str, folder: str) -> list[Dict[str, Any]]:
    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    history = response.get("version_history", [])
    if history:
        return history
    # Legacy response: expose the current metadata as a root version without
    # modifying the file until a real edit is registered.
    return [{
        "investigation_id": response.get("investigation_id", f"{chat_id}/{folder}"),
        "version_id": response.get("version_id"),
        "parent_version_id": response.get("parent_version_id"),
        "created_at": response.get("timestamp"),
        "source": response.get("version_source", "pipeline"),
        "prompt": response.get("prompt", ""),
        "title": response.get("title", folder),
        "response_folder": folder,
        "commands": response.get("commands", []),
        "references": response.get("references", []),
        "evaluation": response.get("evaluation"),
        "artifact_types": response.get("artifact_types", []),
    }]



def record_execution(
    chats_dir: str,
    chat_id: str,
    folder: str,
    *,
    operation: str,
    instruction: str,
    status: str,
    changed_files: Optional[list[str]] = None,
    artifact_types: Optional[list[str]] = None,
    message: str = "",
    plan: Optional[Dict[str, Any]] = None,
    runtime_trace: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append an auditable execution event without creating another hierarchy."""
    from datetime import datetime, timezone
    import hashlib

    meta = _load(chats_dir, chat_id)
    response = get_response(meta, folder)
    if response is None:
        raise KeyError(f"Response folder not found: {folder}")
    now = datetime.now(timezone.utc).isoformat()
    seed = "|".join((chat_id, folder, operation, instruction, now))
    event_id = "exec-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    event = {
        "event_id": event_id,
        "created_at": now,
        "operation": operation,
        "instruction": instruction,
        "status": status,
        "message": message,
        "changed_files": list(changed_files or []),
        "artifact_types": list(artifact_types or []),
        "plan": dict(plan or {}),
        "runtime_trace": dict(runtime_trace or {}),
    }
    response.setdefault("execution_history", []).append(event)
    response["last_execution"] = event
    _save(chats_dir, chat_id, meta)
    return event



def promote_execution_to_version(
    chats_dir: str,
    chat_id: str,
    folder: str,
    *,
    event: Dict[str, Any],
    prompt: str,
    title: str,
    strategy_context: Optional[Dict[str, Any]] = None,
    parent_version_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a succeeded investigation version only after real execution succeeded."""
    if str(event.get("status")) != "ok":
        raise ValueError("Only successful execution events can be promoted to a version")
    return register_version(
        chats_dir,
        chat_id,
        folder,
        prompt=prompt,
        title=title,
        source="artifact_execution",
        commands=[str(event.get("instruction", ""))],
        artifact_types=list(event.get("artifact_types") or []),
        status="succeeded",
        strategy_context=strategy_context or {},
        parent_version_id=parent_version_id,
    )

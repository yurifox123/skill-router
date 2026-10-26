#!/usr/bin/env python3
"""Maintain a small registry and activate user-managed Codex skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if os.name == "nt":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def default_library() -> Path:
    return Path(os.environ.get("SKILL_LIBRARY", Path.home() / ".codex" / "skill-library")).expanduser()


def default_global_roots() -> list[Path]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return [codex_home / "skills", Path.home() / ".agents" / "skills"]


def parse_frontmatter(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return path.parent.name, ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return path.parent.name, ""
    header = parts[1]
    name = re.search(r"^name:\s*(.+)$", header, re.MULTILINE)
    desc = re.search(r"^description:\s*(.*?)(?=^\w[^\n]*:|\Z)", header, re.MULTILINE | re.DOTALL)
    skill_name = (name.group(1).strip() if name else path.parent.name).strip("'\"")
    purpose = " ".join((desc.group(1).strip() if desc else "").split()).strip("'\"")
    return skill_name, purpose


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def token_estimate(path: Path) -> int:
    text = (path / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    return max(1, round(len(text) / 4))


def skill_packages(root: Path) -> list[tuple[Path, Path]]:
    if not root.is_dir():
        return []
    result: list[tuple[Path, Path]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "node_modules":
            continue
        if (child / "SKILL.md").is_file():
            result.append((child, child))
            continue
        nested = [
            path for path in child.glob("*/SKILL.md")
            if "node_modules" not in path.parts
        ]
        if len(nested) == 1:
            # Keep the wrapper directory as the package so scripts and sibling
            # resources remain available after migration.
            result.append((child, nested[0].parent))
    return result


def record(package: Path, metadata_dir: Path, source: str, relative_to: Path | None = None) -> dict:
    name, purpose = parse_frontmatter(metadata_dir / "SKILL.md")
    relative = str(package.relative_to(relative_to)) if relative_to else str(package)
    terms = re.findall(r"[a-z0-9][a-z0-9-]{1,}", f"{name} {purpose.lower()}")
    return {
        "name": name,
        "purpose": purpose,
        "tags": sorted(set(terms))[:32],
        "requires": [],
        "source": source,
        "path": relative,
        "size_bytes": sum(p.stat().st_size for p in package.rglob("*") if p.is_file()),
        "token_estimate": token_estimate(metadata_dir),
        "sha256": sha256_tree(package),
    }


def registry_path(library: Path) -> Path:
    return library / "registry.jsonl"


def registry_markdown_path(library: Path) -> Path:
    return library / "registry.md"


def markdown_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def write_registry(library: Path, records: list[dict]) -> None:
    library.mkdir(parents=True, exist_ok=True)
    with registry_path(library).open("w", encoding="utf-8", newline="\n") as handle:
        for item in sorted(records, key=lambda row: row["name"]):
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    ordered = sorted(records, key=lambda row: row["name"])
    with registry_markdown_path(library).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Skill Registry\n\n")
        handle.write("Generated from the active skill inventory. Edit skill packages or registry metadata at the source, then regenerate.\n\n")
        handle.write("| Skill | Purpose | Tags | Requires | Token estimate | Source | Path |\n")
        handle.write("|---|---|---|---|---:|---|---|\n")
        for item in ordered:
            tags = ", ".join(item.get("tags", []))
            requires = ", ".join(item.get("requires", [])) or "—"
            handle.write(
                "| "
                + " | ".join(
                    [
                        markdown_cell(item.get("name")),
                        markdown_cell(item.get("purpose")),
                        markdown_cell(tags),
                        markdown_cell(requires),
                        markdown_cell(item.get("token_estimate")),
                        markdown_cell(item.get("source")),
                        markdown_cell(item.get("path")),
                    ]
                )
                + " |\n"
            )


def read_registry(library: Path) -> list[dict]:
    path = registry_path(library)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scan_library(library: Path) -> list[dict]:
    return [record(package, metadata, "library", library) for package, metadata in skill_packages(library / "packages")]


def scan_active(roots: list[Path], skip: set[str]) -> list[dict]:
    rows = []
    for root in roots:
        for package, metadata in skill_packages(root):
            name, _ = parse_frontmatter(metadata / "SKILL.md")
            if name in skip or package.name in skip:
                continue
            rows.append(record(package, metadata, str(root), root))
    return rows


def print_rows(rows: list[dict], as_json: bool) -> None:
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for row in rows:
        print(f"{row['name']}\t{row.get('token_estimate', '?')} tokens\t{row.get('purpose', '')}")


def duplicate_names(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["name"], []).append(row)
    return {name: items for name, items in grouped.items() if len(items) > 1}


def command_inventory(args: argparse.Namespace) -> int:
    rows = scan_library(args.library) + scan_active(args.roots, {"skill-router"})
    duplicates = duplicate_names(rows)
    dedup: dict[str, dict] = {}
    for row in rows:
        dedup[row["name"]] = row
    result = list(dedup.values())
    if args.write:
        write_registry(args.library, result)
    print_rows(result, args.json)
    if duplicates and not args.json:
        print("duplicate names:")
        for name, items in sorted(duplicates.items()):
            print(f"  {name}: " + ", ".join(item["source"] for item in items))
    if args.write and not args.json:
        print(f"registry: {registry_path(args.library)}")
        print(f"human-readable registry: {registry_markdown_path(args.library)}")
    return 0


def command_global_init(args: argparse.Namespace) -> int:
    library = args.library
    packages = library / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    candidates = scan_active(args.roots, {"skill-router"})
    if not candidates:
        print("No user-managed global skills found.")
        return 0
    duplicates = duplicate_names(candidates)
    if duplicates:
        details = "; ".join(f"{name} ({len(items)} copies)" for name, items in sorted(duplicates.items()))
        raise SystemExit(f"Duplicate active skill names require manual resolution before migration: {details}")
    for row in candidates:
        source = Path(row["source"]) / row["path"]
        target = packages / row["name"]
        print(f"{source} -> {target}")
        if target.exists():
            raise SystemExit(f"Conflict: library package already exists: {target}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to move these skills.")
        return 0
    for row in candidates:
        source = Path(row["source"]) / row["path"]
        shutil.move(str(source), str(packages / row["name"]))
    write_registry(library, scan_library(library))
    print(f"Moved {len(candidates)} skills and wrote {registry_path(library)}")
    return 0


def project_terms(project: Path) -> set[str]:
    if not project.is_dir():
        return set()
    terms = {p.name.lower() for p in project.iterdir()}
    for filename in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod"):
        path = project / filename
        if path.is_file():
            terms.update(re.findall(r"[a-z0-9][a-z0-9-]{2,}", path.read_text(encoding="utf-8", errors="replace").lower()))
    return terms


def command_recommend(args: argparse.Namespace) -> int:
    rows = read_registry(args.library)
    if not rows:
        raise SystemExit(f"No registry found at {registry_path(args.library)}. Run inventory --write first.")
    query = set(re.findall(r"[a-z0-9][a-z0-9-]{1,}", args.query.lower()))
    terms = query | project_terms(args.project)
    scored = []
    for row in rows:
        haystack = set(row["tags"]) | set(re.findall(r"[a-z0-9][a-z0-9-]{1,}", row["name"].lower()))
        score = len(terms & haystack)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1]["token_estimate"], item[1]["name"]))
    print_rows([row | {"score": score} for score, row in scored[: args.limit]], args.json)
    return 0


def state_path(args: argparse.Namespace) -> Path:
    return args.project / ".project-skills.lock.json" if args.scope == "project" else args.library / "global.json"


def backup_path(library: Path, scope: str, name: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
    return library / "backups" / f"{stamp}-{scope}-{safe_name}"


def command_enable(args: argparse.Namespace) -> int:
    rows = {row["name"]: row for row in read_registry(args.library)}
    if args.name not in rows:
        raise SystemExit(f"Skill not found in registry: {args.name}")
    source = args.library / rows[args.name]["path"]
    if not source.is_dir():
        raise SystemExit(f"Skill package missing: {source}")
    if args.scope == "project":
        if not args.project:
            raise SystemExit("--project is required for project scope")
        target = args.project / ".agents" / "skills" / args.name
    else:
        target = args.global_root / args.name
    if target.exists() and not args.replace:
        raise SystemExit(f"Destination exists: {target}. Use --replace only with explicit authorization.")
    lock = state_path(args)
    state = json.loads(lock.read_text(encoding="utf-8")) if lock.is_file() else {}
    if target.exists():
        backup = backup_path(args.library, args.scope, args.name)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(backup))
        state.setdefault("backups", {})[args.name] = {
            "scope": args.scope,
            "path": str(backup),
            "reason": "replace",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"backed up existing skill to {backup}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    state.setdefault("skills", {})[args.name] = {
        "scope": args.scope,
        "source": str(source),
        "sha256": rows[args.name]["sha256"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"enabled {args.name} at {target}")
    print("Skill discovery normally takes effect in the next turn or session.")
    return 0


def command_disable(args: argparse.Namespace) -> int:
    if args.scope == "project":
        if not args.project:
            raise SystemExit("--project is required for project scope")
        target = args.project / ".agents" / "skills" / args.name
    else:
        target = args.global_root / args.name
    if not target.exists():
        print(f"Not active: {target}")
        return 0
    print(f"remove {target}")
    if not args.apply:
        action = "purge" if args.purge else "archive"
        print(f"Dry run only. Re-run with --apply to {action} the skill.")
        return 0
    lock = state_path(args)
    state = json.loads(lock.read_text(encoding="utf-8")) if lock.is_file() else {}
    if args.purge:
        shutil.rmtree(target)
        print(f"purged {args.name} without a backup")
    else:
        backup = backup_path(args.library, args.scope, args.name)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(backup))
        state.setdefault("backups", {})[args.name] = {
            "scope": args.scope,
            "path": str(backup),
            "reason": "disable",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"archived {args.name} to {backup}")
    state.get("skills", {}).pop(args.name, None)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"disabled {args.name}")
    return 0


def command_restore(args: argparse.Namespace) -> int:
    if args.scope == "project":
        if not args.project:
            raise SystemExit("--project is required for project scope")
        target = args.project / ".agents" / "skills" / args.name
    else:
        target = args.global_root / args.name
    lock = state_path(args)
    if not lock.is_file():
        raise SystemExit(f"No state file found: {lock}")
    state = json.loads(lock.read_text(encoding="utf-8"))
    entry = state.get("backups", {}).get(args.name)
    if not entry or entry.get("scope") != args.scope:
        raise SystemExit(f"No backup found for {args.scope} skill: {args.name}")
    backup = Path(entry["path"])
    if target.exists():
        raise SystemExit(f"Restore destination exists: {target}")
    if not backup.is_dir():
        raise SystemExit(f"Backup missing: {backup}")
    print(f"restore {backup} -> {target}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to restore the skill.")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(backup), str(target))
    state.setdefault("skills", {})[args.name] = {
        "scope": args.scope,
        "source": "restored-backup",
        "sha256": sha256_tree(target),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    state.get("backups", {}).pop(args.name, None)
    lock.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"restored {args.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage on-demand Codex skills.")
    parser.add_argument("--library", type=Path, default=default_library())
    parser.add_argument("--global-root", type=Path, default=default_global_roots()[0])
    parser.add_argument("--root", dest="roots", action="append", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--write", action="store_true")
    inv.add_argument("--json", action="store_true")
    inv.set_defaults(func=command_inventory)
    mig = sub.add_parser("global-init")
    mig.add_argument("--apply", action="store_true")
    mig.set_defaults(func=command_global_init)
    rec = sub.add_parser("recommend")
    rec.add_argument("--project", type=Path, required=True)
    rec.add_argument("--query", required=True)
    rec.add_argument("--limit", type=int, default=5)
    rec.add_argument("--json", action="store_true")
    rec.set_defaults(func=command_recommend)
    for name, func in (("enable", command_enable), ("disable", command_disable), ("restore", command_restore)):
        cmd = sub.add_parser(name)
        cmd.add_argument("--name", required=True)
        cmd.add_argument("--scope", choices=("global", "project"), required=True)
        cmd.add_argument("--project", type=Path)
        cmd.add_argument("--replace", action="store_true")
        cmd.add_argument("--apply", action="store_true")
        if name == "disable":
            cmd.add_argument("--purge", action="store_true")
        cmd.set_defaults(func=func)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.roots is None:
        args.roots = default_global_roots()
    args.library = args.library.expanduser().resolve()
    args.global_root = args.global_root.expanduser().resolve()
    if getattr(args, "project", None):
        args.project = args.project.expanduser().resolve()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

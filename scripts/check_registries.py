import argparse
import json
import sys
from pathlib import Path

import nbtlib
import requests

NAMESPACE  = "mbs"
MC_VERSION = "1.21"

REGISTRY_URL = (
    f"https://raw.githubusercontent.com/misode/mcmeta"
    f"/{MC_VERSION}-summary/registries/data.json"
)

CACHE_DIR        = Path(__file__).parent / ".cache"
CACHE_ITEM_FILE  = CACHE_DIR / f"registry_item_{MC_VERSION}.json"
CACHE_BLOCK_FILE = CACHE_DIR / f"registry_block_{MC_VERSION}.json"


def fetch_registries() -> dict:
    print(f"Fetching registries from misode/mcmeta ({MC_VERSION}-summary) ...")
    response = requests.get(REGISTRY_URL, timeout=15)
    response.raise_for_status()
    return response.json()


def load_registries(refresh: bool) -> tuple[set[str], set[str]]:
    if not refresh and CACHE_ITEM_FILE.exists() and CACHE_BLOCK_FILE.exists():
        with open(CACHE_ITEM_FILE, encoding="utf-8") as f:
            items = set(json.load(f))
        with open(CACHE_BLOCK_FILE, encoding="utf-8") as f:
            blocks = set(json.load(f))
        return items, blocks

    data   = fetch_registries()
    items  = data.get("item", [])
    blocks = data.get("block", [])

    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_ITEM_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    with open(CACHE_BLOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(blocks, f, indent=2)

    rel = CACHE_DIR.relative_to(Path(__file__).parent.parent)
    print(f"[OK] Registries cached to {rel}/")
    return set(items), set(blocks)


def collect_item_names(node, path: str, results: list):
    # Walk loot table JSON; collect (json_path, name) for minecraft: item references
    if isinstance(node, dict):
        obj_type = node.get("type", "")
        obj_func = node.get("function", "")
        name_val = node.get("name")

        if isinstance(name_val, str) and name_val.startswith("minecraft:"):
            is_item_entry = obj_type == "minecraft:item"
            is_item_func  = isinstance(obj_func, str) and obj_func.startswith("minecraft:")
            if is_item_entry or is_item_func:
                item_path = f"{path}.name" if path else "name"
                results.append((item_path, name_val))

        for k, v in node.items():
            child_path = f"{path}.{k}" if path else k
            collect_item_names(v, child_path, results)

    elif isinstance(node, list):
        for i, child in enumerate(node):
            collect_item_names(child, f"{path}[{i}]", results)


def check_loot_tables(loot_dir: Path, item_registry: set[str]) -> list[tuple[str, str, str]]:
    violations = []
    for path in sorted(loot_dir.rglob("*.json")):
        rel = str(path.relative_to(loot_dir))
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  [WARN] {rel} — invalid JSON: {e}")
            continue

        found: list[tuple[str, str]] = []
        collect_item_names(data, "", found)

        for json_path, name in found:
            bare = name[len("minecraft:"):]
            if bare not in item_registry:
                violations.append((rel, name, json_path))

    return violations


def check_nbt_palettes(structure_dir: Path, block_registry: set[str]) -> list[tuple[str, str]]:
    violations = []
    for path in sorted(structure_dir.rglob("*.nbt")):
        rel = str(path.relative_to(structure_dir))
        try:
            nbtfile = nbtlib.load(str(path))
        except Exception as e:
            print(f"  [WARN] {rel} — could not read NBT: {e}")
            continue

        palette = nbtfile.get("palette", [])
        for entry in palette:
            name = str(entry.get("Name", ""))
            if not name.startswith("minecraft:"):
                continue
            bare = name[len("minecraft:"):]
            if bare not in block_registry:
                violations.append((rel, name))

    return violations


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description=f"Validate minecraft: namespace names in {NAMESPACE} against MC {MC_VERSION} registries."
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="Re-download registry caches even if they already exist.",
    )
    args = parser.parse_args()

    script_dir    = Path(__file__).parent
    project_root  = script_dir.parent
    loot_dir      = project_root / "src" / "main" / "resources" / "data" / NAMESPACE / "loot_table"
    structure_dir = project_root / "src" / "main" / "resources" / "data" / NAMESPACE / "structure"

    if not loot_dir.exists():
        print(f"ERROR: loot_table directory not found:\n  {loot_dir}")
        sys.exit(1)
    if not structure_dir.exists():
        print(f"ERROR: structure directory not found:\n  {structure_dir}")
        sys.exit(1)

    item_registry, block_registry = load_registries(args.refresh)

    # --- Check 1: loot table item names ---
    section(f"CHECK 1 — LOOT TABLE ITEM NAMES  (MC {MC_VERSION})")
    loot_files      = sorted(loot_dir.rglob("*.json"))
    loot_violations = check_loot_tables(loot_dir, item_registry)

    if loot_violations:
        print(f"\n  [FAIL] {len(loot_violations)} invalid item name(s) found:\n")
        for filename, name, json_path in loot_violations:
            print(f"  {filename}")
            print(f"    {json_path}  —  {name}")
    else:
        print(f"\n  [OK] All minecraft: item names in {len(loot_files)} loot table(s) are valid.")

    # --- Check 2: NBT block palette names ---
    section(f"CHECK 2 — NBT BLOCK PALETTE NAMES  (MC {MC_VERSION})")
    nbt_files      = sorted(structure_dir.rglob("*.nbt"))
    nbt_violations = check_nbt_palettes(structure_dir, block_registry)

    if nbt_violations:
        print(f"\n  [FAIL] {len(nbt_violations)} invalid block name(s) found:\n")
        for filename, name in nbt_violations:
            print(f"  {filename}  —  {name}")
    else:
        print(f"\n  [OK] All minecraft: block names in {len(nbt_files)} NBT file(s) are valid.")

    # --- Summary ---
    section("SUMMARY")
    total = len(loot_violations) + len(nbt_violations)
    print(f"\n  Loot table files scanned : {len(loot_files)}")
    print(f"  NBT files scanned        : {len(nbt_files)}")
    print(f"  Total violations         : {total}")

    if total:
        print(f"\n  [FAIL] {total} violation(s) found.")
    else:
        print("\n  [OK] No violations found.")
    print("=" * 60)

    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass

    if total:
        sys.exit(1)


if __name__ == "__main__":
    main()

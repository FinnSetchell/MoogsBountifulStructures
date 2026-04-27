"""
Validates the data chain:
  structure_set -> worldgen/structure -> worldgen/template_pool -> structure/*.nbt

Checks:
  1. Template pool locations -> NBT files exist
  2. Orphaned NBT files (not referenced by any pool)
  3. Worldgen structure start_pool -> template pool exists
  4. Structure set structures -> worldgen structure exists
"""

from pathlib import Path
import json
import sys

NAMESPACE = "mbs"


def loc_to_path(location: str, base_dir: Path, ext: str) -> Path | None:
    """
    Converts 'mbs:some/path' to base_dir / 'some/path<ext>'.
    Returns None if the namespace isn't ours.
    """
    if ":" not in location:
        return None
    namespace, path = location.split(":", 1)
    if namespace != NAMESPACE:
        return None
    return base_dir / (path + ext)


def load_json(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [ERROR] Could not read {path.name}: {e}")
        return None


def collect_pool_locations(pool_data: dict) -> list[str]:
    """Returns all mbs: structure locations referenced in a template pool."""
    locations = []
    for entry in pool_data.get("elements", []):
        element = entry.get("element", {})
        loc = element.get("location")
        if loc:
            locations.append(loc)
        # also handle the versioned 'locations' dict added by update_template_pools.py
        for versioned_loc in element.get("locations", {}).values():
            locations.append(versioned_loc)
    return locations


def check_pool_to_nbt(template_pool_dir: Path, structure_dir: Path) -> list[str]:
    """Check 1: every location in every template pool has a matching .nbt file."""
    errors = []
    for json_path in sorted(template_pool_dir.rglob("*.json")):
        data = load_json(json_path)
        if data is None:
            continue
        pool_rel = json_path.relative_to(template_pool_dir)
        for loc in collect_pool_locations(data):
            nbt_path = loc_to_path(loc, structure_dir, ".nbt")
            if nbt_path is None:
                continue  # skip non-mbs locations
            if not nbt_path.exists():
                errors.append(f"  {pool_rel}  ->  {loc}  (no matching .nbt)")
    return errors


def check_orphaned_nbt(template_pool_dir: Path, structure_dir: Path) -> list[str]:
    """Check 2: NBT files that aren't referenced by any template pool."""
    referenced: set[Path] = set()
    for json_path in sorted(template_pool_dir.rglob("*.json")):
        data = load_json(json_path)
        if data is None:
            continue
        for loc in collect_pool_locations(data):
            nbt_path = loc_to_path(loc, structure_dir, ".nbt")
            if nbt_path:
                referenced.add(nbt_path.resolve())

    orphans = []
    for nbt_path in sorted(structure_dir.rglob("*.nbt")):
        if nbt_path.resolve() not in referenced:
            orphans.append(str(nbt_path.relative_to(structure_dir)))
    return orphans


def check_structure_to_pool(structure_dir: Path, template_pool_dir: Path) -> list[str]:
    """Check 3: every worldgen/structure start_pool references an existing template pool."""
    errors = []
    for json_path in sorted(structure_dir.rglob("*.json")):
        data = load_json(json_path)
        if data is None:
            continue
        start_pool = data.get("start_pool")
        if not start_pool:
            continue
        pool_path = loc_to_path(start_pool, template_pool_dir, ".json")
        if pool_path is None:
            continue  # non-mbs pool, skip
        if not pool_path.exists():
            rel = json_path.relative_to(structure_dir)
            errors.append(f"  {rel}  ->  {start_pool}  (pool not found)")
    return errors


def check_set_to_structure(structure_set_dir: Path, worldgen_structure_dir: Path) -> list[str]:
    """Check 4: every structure_set entry references an existing worldgen/structure."""
    errors = []
    for json_path in sorted(structure_set_dir.rglob("*.json")):
        data = load_json(json_path)
        if data is None:
            continue
        rel = json_path.relative_to(structure_set_dir)
        for entry in data.get("structures", []):
            structure_loc = entry.get("structure", "")
            struct_path = loc_to_path(structure_loc, worldgen_structure_dir, ".json")
            if struct_path is None:
                continue  # non-mbs structure, skip
            if not struct_path.exists():
                errors.append(f"  {rel}  ->  {structure_loc}  (worldgen structure not found)")
    return errors


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    script_dir    = Path(__file__).parent
    project_root  = script_dir.parent
    data_dir      = project_root / "src" / "main" / "resources" / "data" / NAMESPACE

    structure_dir         = data_dir / "structure"
    template_pool_dir     = data_dir / "worldgen" / "template_pool"
    worldgen_structure_dir = data_dir / "worldgen" / "structure"
    structure_set_dir     = data_dir / "worldgen" / "structure_set"

    for d in [structure_dir, template_pool_dir, worldgen_structure_dir, structure_set_dir]:
        if not d.exists():
            print(f"ERROR: Directory not found: {d}")
            sys.exit(1)

    failed = False

    # --- Check 1 ---
    section("1/4  Template pool locations -> NBT files")
    errors = check_pool_to_nbt(template_pool_dir, structure_dir)
    if errors:
        print(f"\n[FAIL] {len(errors)} missing NBT file(s):\n")
        for e in errors:
            print(e)
        failed = True
    else:
        print("\n[OK] All pool locations resolve to an existing .nbt file.")

    # --- Check 2 ---
    section("2/4  Orphaned NBT files (not in any pool)")
    orphans = check_orphaned_nbt(template_pool_dir, structure_dir)
    if orphans:
        print(f"\n[WARN] {len(orphans)} .nbt file(s) not referenced by any template pool:\n")
        for o in orphans:
            print(f"  {o}")
    else:
        print("\n[OK] All .nbt files are referenced by at least one template pool.")

    # --- Check 3 ---
    section("3/4  Worldgen structures -> template pools")
    errors = check_structure_to_pool(worldgen_structure_dir, template_pool_dir)
    if errors:
        print(f"\n[FAIL] {len(errors)} missing template pool(s):\n")
        for e in errors:
            print(e)
        failed = True
    else:
        print("\n[OK] All worldgen structures point to existing template pools.")

    # --- Check 4 ---
    section("4/4  Structure sets -> worldgen structures")
    errors = check_set_to_structure(structure_set_dir, worldgen_structure_dir)
    if errors:
        print(f"\n[FAIL] {len(errors)} missing worldgen structure(s):\n")
        for e in errors:
            print(e)
        failed = True
    else:
        print("\n[OK] All structure sets point to existing worldgen structures.")

    print(f"\n{'=' * 60}")
    if failed:
        print("  RESULT: FAILED")
    else:
        print("  RESULT: ALL CHECKS PASSED")
    print('=' * 60)

    if failed:
        sys.exit(1)

    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()

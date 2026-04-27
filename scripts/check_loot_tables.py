import nbtlib as nbt
from pathlib import Path
import collections
import sys

NAMESPACE = "mbs"


def collect_loot_tables(node, out: set):
    """Recursively walk the NBT tree and collect all LootTable string values."""
    if isinstance(node, nbt.Compound):
        for key, val in node.items():
            if key == "LootTable" and isinstance(val, nbt.String):
                out.add(str(val))
            else:
                collect_loot_tables(val, out)
    elif isinstance(node, nbt.List):
        for item in node:
            collect_loot_tables(item, out)


def resource_location_to_path(location: str, loot_table_dir: Path) -> Path | None:
    """
    Converts a resource location like 'mbs:chests/some_chest' to an absolute path
    under the loot_table directory. Returns None if the namespace isn't ours.
    """
    if ":" not in location:
        return None
    namespace, path = location.split(":", 1)
    if namespace != NAMESPACE:
        return None
    return loot_table_dir / (path + ".json")


def main():
    script_dir    = Path(__file__).parent
    project_root  = script_dir.parent
    structure_dir = project_root / "src" / "main" / "resources" / "data" / NAMESPACE / "structure"
    loot_table_dir = project_root / "src" / "main" / "resources" / "data" / NAMESPACE / "loot_table"

    if not structure_dir.exists():
        print(f"ERROR: Structure directory not found:\n  {structure_dir}")
        sys.exit(1)
    if not loot_table_dir.exists():
        print(f"ERROR: Loot table directory not found:\n  {loot_table_dir}")
        sys.exit(1)

    # structure nbt path -> set of loot table resource locations used
    structure_tables: dict[str, set[str]] = {}

    for nbt_path in sorted(structure_dir.rglob("*.nbt")):
        rel = str(nbt_path.relative_to(structure_dir).with_suffix("")).replace("\\", "/")
        try:
            nbtfile = nbt.load(str(nbt_path))
        except Exception as e:
            print(f"  [ERROR] {rel}.nbt — {e}")
            continue

        tables: set[str] = set()
        collect_loot_tables(nbtfile, tables)
        structure_tables[rel] = tables

    # categorise each unique loot table reference
    all_refs: set[str] = set()
    for tables in structure_tables.values():
        all_refs |= tables

    missing: dict[str, list[str]] = collections.defaultdict(list)  # loot table -> structures that use it
    minecraft_refs: dict[str, list[str]] = collections.defaultdict(list)
    other_refs: dict[str, list[str]] = collections.defaultdict(list)

    for ref in sorted(all_refs):
        if ":" not in ref:
            other_refs[ref] = []
            continue
        namespace, _ = ref.split(":", 1)
        if namespace == "minecraft":
            for struct, tables in structure_tables.items():
                if ref in tables:
                    minecraft_refs[ref].append(struct)
        elif namespace == NAMESPACE:
            path = resource_location_to_path(ref, loot_table_dir)
            if path and not path.exists():
                for struct, tables in structure_tables.items():
                    if ref in tables:
                        missing[ref].append(struct)
        else:
            for struct, tables in structure_tables.items():
                if ref in tables:
                    other_refs[ref].append(struct)

    # --- Report ---
    print("=" * 60)
    print("LOOT TABLE AUDIT")
    print("=" * 60)

    if missing:
        print(f"\n[MISSING] {len(missing)} loot table(s) referenced but not found in project:\n")
        for ref, structs in sorted(missing.items()):
            expected = resource_location_to_path(ref, loot_table_dir)
            expected_rel = expected.relative_to(loot_table_dir) if expected else ref
            print(f"  {ref}  (expected file: {expected_rel})")
            for s in sorted(structs):
                print(f"    used by: {s}")
    else:
        print("\n[OK] All mbs: loot tables exist in the project.")

    if minecraft_refs:
        print(f"\n[MINECRAFT] {len(minecraft_refs)} vanilla loot table(s) used (minecraft: namespace):\n")
        for ref, structs in sorted(minecraft_refs.items()):
            print(f"  {ref}")
            for s in sorted(structs):
                print(f"    used by: {s}")

    if other_refs:
        print(f"\n[UNKNOWN NAMESPACE] {len(other_refs)} loot table(s) with unrecognised namespace:\n")
        for ref, structs in sorted(other_refs.items()):
            print(f"  {ref}")
            for s in sorted(structs):
                print(f"    used by: {s}")

    if not missing and not minecraft_refs and not other_refs:
        print("\nNo issues found.")

    with_loot    = sum(1 for t in structure_tables.values() if t)
    without_loot = len(structure_tables) - with_loot
    print(f"\n{len(structure_tables)} structure(s) scanned total — {with_loot} with loot tables, {without_loot} without.")

    if missing or other_refs:
        sys.exit(1)

    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()

"""
For each of the 12 converted structure NBTs, finds the template pool elements
that reference them and upgrades those elements from:

    "element_type": "minecraft:single_pool_element"
    "location": "mbs:<name>"

to:

    "element_type": "moogs_structures:versioned_single_pool_element"
    "location": "mbs:<name>"          <- default (used for all other versions)
    "locations": {
      "1.20.5-1.20.6": "mbs:1_20_5/<name>"
    }

Only elements whose location exactly matches one of the 12 converted structure
names are touched; all other elements are left alone.
"""

import json
from pathlib import Path

POOL_DIR = (
    Path(__file__).parent.parent
    / "src" / "main" / "resources" / "data" / "mbs" / "worldgen" / "template_pool"
)

# The 12 NBT filenames that were converted (without .nbt extension = structure base name)
CONVERTED = {
    "big_pale_house_1",
    "building_remains",
    "dead_pine_cart1",
    "dead_pine_cart_2",
    "dead_wood_cart",
    "dead_wood_church",
    "desert_cart_1",
    "desert_pine_cart2",
    "jungle_pine_cart1",
    "jungle_pine_cart2",
    "plainsandgrass_pine_cart",
    "plainsandgrass_pine_cart_2",
}

NAMESPACE = "mbs"
VERSION_RANGE = "1.20.5-1.20.6"
BACKUP_FOLDER = "1_20_5"


def structure_name_from_location(location: str) -> str | None:
    """'mbs:dead_wood_cart' -> 'dead_wood_cart', or None if wrong namespace."""
    prefix = NAMESPACE + ":"
    if not location.startswith(prefix):
        return None
    rest = location[len(prefix):]
    # skip if it already has a subfolder (versioned location)
    if "/" in rest:
        return None
    return rest


def upgrade_element(element: dict) -> bool:
    """Mutates element in-place. Returns True if changed."""
    location = element.get("location", "")
    name = structure_name_from_location(location)
    if name not in CONVERTED:
        return False
    if element.get("element_type") == "moogs_structures:versioned_single_pool_element":
        return False  # already upgraded

    element["element_type"] = "moogs_structures:versioned_single_pool_element"
    element["locations"] = {
        VERSION_RANGE: f"{NAMESPACE}:{BACKUP_FOLDER}/{name}"
    }
    return True


def process_pool(json_path: Path) -> bool:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    modified = False
    for entry in data.get("elements", []):
        if upgrade_element(entry.get("element", {})):
            modified = True

    if modified:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    return modified


def main():
    updated = []
    skipped = []

    for json_path in sorted(POOL_DIR.rglob("*.json")):
        rel = json_path.relative_to(POOL_DIR)
        if process_pool(json_path):
            updated.append(str(rel))
            print(f"  [UPDATED] {rel}")
        else:
            skipped.append(str(rel))

    print(f"\nDone! {len(updated)} pool file(s) updated, {len(skipped)} unchanged.")
    if updated:
        print("\nUpdated files:")
        for f in updated:
            print(f"  {f}")


if __name__ == "__main__":
    main()

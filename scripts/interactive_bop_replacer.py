import nbtlib as nbt
from pathlib import Path
import collections.abc
import sys
import re

MISSING_BLOCKS = {
    'black_flower_petal_block', 'blue_flower_petal_block', 'brown_flower_petal_block', 'cyan_flower_petal_block',
    'dead_fence_gate', 'dead_shelf', 'empyreal_fence_gate', 'empyreal_shelf', 'fir_shelf', 'flower_bud',
    'flower_stem', 'gray_flower_petal_block', 'green_flower_petal_block', 'hellbark_fence_gate', 'hellbark_shelf',
    'jacaranda_fence_gate', 'jacaranda_shelf', 'light_blue_flower_petal_block', 'light_gray_flower_petal_block',
    'lime_flower_petal_block', 'magenta_flower_petal_block', 'magic_fence_gate', 'magic_shelf', 'mahogany_fence_gate',
    'mahogany_shelf', 'maple_shelf', 'marigold', 'orange_flower_petal_block', 'orange_maple_leaf_litter',
    'origin_dandelion', 'origin_oak_button', 'origin_oak_door', 'origin_oak_fence', 'origin_oak_fence_gate',
    'origin_oak_hanging_sign', 'origin_oak_leaves', 'origin_oak_log', 'origin_oak_planks', 'origin_oak_pressure_plate',
    'origin_oak_sapling', 'origin_oak_shelf', 'origin_oak_sign', 'origin_oak_slab', 'origin_oak_stairs',
    'origin_oak_trapdoor', 'origin_oak_wall_hanging_sign', 'origin_oak_wall_sign', 'origin_oak_wood', 'origin_rose',
    'palm_fence_gate', 'palm_shelf', 'pine_fence_gate', 'pine_shelf', 'pink_flower_petal_block', 'potted_flower_bud',
    'potted_marigold', 'potted_origin_dandelion', 'potted_origin_oak_sapling', 'potted_origin_rose', 'potted_voidcap',
    'purple_flower_petal_block', 'purple_wildflowers', 'red_flower_petal_block', 'red_maple_leaf_litter', 'redwood_shelf',
    'stripped_origin_oak_log', 'stripped_origin_oak_wood', 'umbran_fence_gate', 'umbran_shelf', 'voidcap',
    'voidcap_block', 'white_flower_petal_block', 'willow_fence_gate', 'willow_shelf', 'yellow_flower_petal_block',
    'yellow_maple_leaf_litter'
}

def extract_block_name(s):
    # Try to extract the block ID, e.g. "biomesoplenty:dead_fence_gate" or "biomesoplenty:dead_fence_gate[facing=north]"
    match = re.search(r'biomesoplenty:([a-zA-Z0-9_]+)', s)
    if match:
        return match.group(1), match.group(0)
    return None, None

def find_missing_blocks_in_nbt(node, found_blocks):
    """Recursively walk the NBT tree to find any missing BOP blocks."""
    if isinstance(node, collections.abc.Mapping):
        for key in list(node.keys()):
            entry = node[key]
            if isinstance(entry, (nbt.List, nbt.Compound)):
                find_missing_blocks_in_nbt(entry, found_blocks)
            elif isinstance(entry, nbt.String):
                block_name, full_id = extract_block_name(str(entry))
                if block_name and block_name in MISSING_BLOCKS:
                    found_blocks.add(full_id)
    elif isinstance(node, nbt.List):
        for entry in node:
            if isinstance(entry, (nbt.List, nbt.Compound)):
                find_missing_blocks_in_nbt(entry, found_blocks)
            elif isinstance(entry, nbt.String):
                block_name, full_id = extract_block_name(str(entry))
                if block_name and block_name in MISSING_BLOCKS:
                    found_blocks.add(full_id)

def replace_strings(node, replacements, changed):
    """Recursively walk the NBT tree, replacing strings in-place."""
    if isinstance(node, collections.abc.Mapping):
        for key in list(node.keys()):
            entry = node[key]
            if isinstance(entry, (nbt.List, nbt.Compound)):
                replace_strings(entry, replacements, changed)
            elif isinstance(entry, nbt.String):
                result = _replace(str(entry), replacements)
                if result is not None:
                    node[key] = nbt.String(result)
                    changed[0] = True
    elif isinstance(node, nbt.List):
        for i, entry in enumerate(node):
            if isinstance(entry, (nbt.List, nbt.Compound)):
                replace_strings(entry, replacements, changed)
            elif isinstance(entry, nbt.String):
                result = _replace(str(entry), replacements)
                if result is not None:
                    node[i] = nbt.String(result)
                    changed[0] = True

def _replace(s, replacements):
    original = s
    for old, new in replacements.items():
        s = re.sub(re.escape(old) + r'(?![a-zA-Z0-9_])', new, s)
    return s if s != original else None

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    structure_dir = project_root / "src" / "main" / "resources" / "data" / "mbs" / "structures"

    if not structure_dir.exists():
        print(f"ERROR: Structure directory not found:\n  {structure_dir}")
        sys.exit(1)

    print(f"Scanning: {structure_dir}\n")

    saved = []
    skipped = []

    for nbt_path in sorted(structure_dir.rglob("*.nbt")):
        rel = nbt_path.relative_to(structure_dir)
        
        try:
            nbtfile = nbt.load(str(nbt_path))
        except Exception as e:
            print(f"[ERROR]   {rel} — {e}")
            continue
            
        found_blocks = set()
        find_missing_blocks_in_nbt(nbtfile, found_blocks)
        
        if not found_blocks:
            skipped.append(str(rel))
            continue
            
        print(f"\n--- Found missing blocks in: {rel} ---")
        replacements = {}
        for block_id in sorted(found_blocks):
            new_id = input(f"Replace '{block_id}' with: ").strip()
            if new_id:
                replacements[block_id] = new_id
                
        if replacements:
            changed = [False]
            replace_strings(nbtfile, replacements, changed)
            if changed[0]:
                nbtfile.save(str(nbt_path))
                saved.append(str(rel))
                print(f"  [SAVED]   {rel}")
            else:
                print(f"  [WARNING] Replacements specified but no changes were made to {rel}")
        else:
            print(f"  [SKIPPED] No replacements specified for {rel}")

    print(f"\nDone! {len(saved)} file(s) updated, {len(skipped)} had no missing blocks.")

if __name__ == "__main__":
    main()

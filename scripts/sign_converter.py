"""
Converts sign block entity NBT from 1.21 format to 1.20 format.

Changes made per sign block entity:
  1. Removes the "components" key (added in 1.21, not recognised in 1.20).
  2. Rewrites each message string from {"text": "..."} (space after colon)
     to {"text":"..."} (no space), matching the compact JSON format 1.20 uses.

For each affected file the original is copied to structures/1_20_5/ first,
then the converted version overwrites the original path.
"""

import nbtlib as nbt
import json
import shutil
from pathlib import Path


STRUCTURE_DIR = Path(__file__).parent.parent / "src" / "main" / "resources" / "data" / "mbs" / "structures"
BACKUP_FOLDER = "1_20_5"


def compact_message(msg_str: str) -> str:
    """
    Parse the JSON string stored in a sign message and re-serialise it
    without spaces after colons or commas, matching the 1.20 format.
    If the string is not valid JSON we leave it alone.
    """
    try:
        parsed = json.loads(msg_str)
        return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return msg_str


def is_sign_entity(block_nbt) -> bool:
    id_val = str(block_nbt.get("id", "")).lower()
    return "sign" in id_val


def convert_sign_entity(block_nbt) -> bool:
    """
    Mutates block_nbt in-place to remove "components" and compact messages.
    Returns True if any change was actually made.
    """
    changed = False

    # 1. Remove "components" if present
    if "components" in block_nbt:
        del block_nbt["components"]
        changed = True

    # 2. Compact message strings in front_text and back_text
    for side in ("front_text", "back_text"):
        side_compound = block_nbt.get(side)
        if side_compound is None:
            continue
        messages = side_compound.get("messages")
        if messages is None:
            continue
        for i, msg in enumerate(messages):
            original = str(msg)
            compacted = compact_message(original)
            if compacted != original:
                messages[i] = nbt.String(compacted)
                changed = True

    return changed


def main():
    if not STRUCTURE_DIR.exists():
        print(f"ERROR: Structure directory not found:\n  {STRUCTURE_DIR}")
        return

    backup_base = STRUCTURE_DIR / BACKUP_FOLDER
    print(f"Scanning: {STRUCTURE_DIR}")
    print(f"Backup:   {backup_base}\n")

    saved   = []
    skipped = []

    for nbt_path in sorted(STRUCTURE_DIR.rglob("*.nbt")):
        rel = nbt_path.relative_to(STRUCTURE_DIR)

        # skip files already inside a version subfolder (first part starts with a digit)
        if rel.parts[0][0].isdigit():
            continue

        try:
            nbtfile = nbt.load(str(nbt_path))
        except Exception as e:
            print(f"  [ERROR]   {rel} — {e}")
            continue

        file_changed = False
        blocks = nbtfile.get("blocks", [])
        for block in blocks:
            block_nbt = block.get("nbt")
            if block_nbt is None:
                continue
            if is_sign_entity(block_nbt):
                if convert_sign_entity(block_nbt):
                    file_changed = True

        if file_changed:
            # back up original to 1_20_5/ before overwriting
            backup_path = backup_base / rel
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(nbt_path), str(backup_path))
            # overwrite original with converted version
            nbtfile.save(str(nbt_path))
            saved.append(str(rel))
            print(f"  [CONVERTED] {rel}")
        else:
            skipped.append(str(rel))
            print(f"  [skipped]   {rel}")

    print(f"\nDone! {len(saved)} file(s) converted, originals backed up to '{BACKUP_FOLDER}/', {len(skipped)} unchanged.")
    if saved:
        print("\nConverted files:")
        for f in saved:
            print(f"  {f}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import jsonschema
import referencing
import referencing.jsonschema
import requests

NAMESPACE  = "mbs"
MC_VERSION = "1.21"

# misode/mcmeta does not contain JSON Schema files. The nearest source is
# misode/minecraft-json-schemas (a mirror of Levertion/minecraft-json-schemas).
# That schema predates namespaced entry types and typed roll distributions, so
# patch_schema() brings it up to MC 1.21 before validation.
SCHEMA_URL = (
    "https://raw.githubusercontent.com/misode/minecraft-json-schemas"
    "/master/java/data/loot_table.json"
)

CACHE_DIR      = Path(__file__).parent / ".cache"
CACHE_FILE     = CACHE_DIR / f"loot_table_schema_{MC_VERSION}.json"
REFS_CACHE_DIR = CACHE_DIR / "refs"


def fetch_schema() -> dict:
    print("Fetching loot table schema from misode/minecraft-json-schemas ...")
    response = requests.get(SCHEMA_URL, timeout=15)
    response.raise_for_status()
    return response.json()


def load_schema(refresh: bool) -> dict:
    if not refresh and CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)

    schema = fetch_schema()
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"[OK] Schema cached to {CACHE_FILE.relative_to(Path(__file__).parent.parent)}")
    return schema


def resolve_refs(node, base_url: str):
    # Replace relative $ref paths with absolute URLs so the registry retriever
    # always receives a fetchable HTTP URL.
    if isinstance(node, dict):
        result = {}
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str) and not v.startswith("#") and "://" not in v:
                result[k] = urljoin(base_url, v)
            else:
                result[k] = resolve_refs(v, base_url)
        return result
    if isinstance(node, list):
        return [resolve_refs(item, base_url) for item in node]
    return node


# Schema for a roll value: plain number, old {min,max}, or 1.14+ typed distribution.
_RANGE_SCHEMA = {
    "oneOf": [
        {"type": ["number", "integer"]},
        {"type": "object"},
    ]
}

# Permissive per-entry schema for MC 1.21.
# The upstream schema used bare type names ("item") and didn't know about
# namespaced types ("minecraft:item") or newer entry kinds added in 1.13+.
_ENTRY_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type":       {"type": "string"},
        "name":       {"type": "string"},
        "weight":     {"type": ["number", "integer"]},
        "quality":    {"type": ["number", "integer"]},
        "functions":  {"type": "array"},
        "conditions": {"type": "array"},
        "children":   {"type": "array"},
        "entries":    {"type": "array"},
        "expand":     {"type": "boolean"},
        "value":      {},
    },
}


def patch_schema(schema: dict) -> dict:
    patched = copy.deepcopy(schema)

    # Root: drop the additionalProperties guard and add fields missing from
    # the upstream schema (added to Minecraft in 1.13 / 1.14).
    patched.pop("additionalProperties", None)
    root_props = patched.setdefault("properties", {})
    root_props.pop("additionalProperties", None)  # was mistakenly placed inside properties
    root_props["type"]            = {"type": "string"}
    root_props["random_sequence"] = {"type": "string"}

    pool_items = root_props.get("pools", {}).get("items", {})
    if pool_items:
        pool_items.pop("additionalProperties", None)
        pool_props = pool_items.get("properties", {})

        # Rolls: accept typed distributions like {"type": "minecraft:uniform", ...}
        if "rolls" in pool_props:
            pool_props["rolls"] = _RANGE_SCHEMA
        if "bonus_rolls" in pool_props:
            pool_props["bonus_rolls"] = _RANGE_SCHEMA

        # Entries: replace the strict pre-1.13 oneOf with a permissive 1.21 schema.
        entries_schema = pool_props.get("entries", {})
        if entries_schema:
            entries_items = entries_schema.get("items", {})
            entries_items.pop("oneOf", None)
            entries_items.pop("required", None)
            entries_items.pop("additionalProperties", None)
            entries_items.update(_ENTRY_SCHEMA)

    # Functions: accept any string function name (many were added post-1.12).
    defs = patched.get("definitions", {})
    if "function" in defs:
        defs["function"] = {
            "type": "object",
            "required": ["function"],
            "properties": {"function": {"type": "string"}},
        }

    return patched


def make_retriever(refresh: bool):
    REFS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def retrieve(uri: str) -> referencing.Resource:
        cache_path = REFS_CACHE_DIR / (hashlib.md5(uri.encode()).hexdigest() + ".json")
        if not refresh and cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                contents = json.load(f)
        else:
            response = requests.get(uri, timeout=15)
            response.raise_for_status()
            contents = response.json()
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(contents, f, indent=2)
        return referencing.Resource.from_contents(
            contents,
            default_specification=referencing.jsonschema.DRAFT4,
        )

    return retrieve


def format_path(error: jsonschema.ValidationError) -> str:
    parts = []
    for step in error.absolute_path:
        if isinstance(step, int):
            parts.append(f"[{step}]")
        else:
            parts.append(f".{step}" if parts else step)
    return "".join(parts) if parts else "<root>"


def validate_file(path: Path, validator: jsonschema.protocols.Validator) -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    return [
        f"{format_path(err)}  —  {err.message}"
        for err in validator.iter_errors(data)
    ]


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description=f"Validate {NAMESPACE} loot tables against the MC {MC_VERSION} schema.",
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="Re-download the schema even if a cached copy exists.",
    )
    args = parser.parse_args()

    script_dir   = Path(__file__).parent
    project_root = script_dir.parent
    loot_dir     = (
        project_root / "src" / "main" / "resources" / "data" / NAMESPACE / "loot_table"
    )

    if not loot_dir.exists():
        print(f"ERROR: loot_table directory not found:\n  {loot_dir}")
        sys.exit(1)

    schema    = load_schema(args.refresh)
    schema    = resolve_refs(schema, SCHEMA_URL)  # resolve against misode URL, not Levertion $id
    schema    = patch_schema(schema)
    retriever = make_retriever(args.refresh)
    registry  = referencing.Registry(retrieve=retriever)

    validator_cls = jsonschema.Draft4Validator
    validator_cls.check_schema(schema)
    validator = validator_cls(schema, registry=registry)

    json_files = sorted(loot_dir.rglob("*.json"))
    if not json_files:
        print("No loot table JSON files found.")
        sys.exit(0)

    section(f"LOOT TABLE SCHEMA VALIDATION  (MC {MC_VERSION})")
    print(f"\n  Validating {len(json_files)} file(s) under:")
    print(f"  {loot_dir.relative_to(project_root)}\n")

    passed   = 0
    failed   = 0
    failures: list[tuple[str, list[str]]] = []

    for path in json_files:
        rel  = path.relative_to(loot_dir)
        errs = validate_file(path, validator)
        if errs:
            failed += 1
            failures.append((str(rel), errs))
            print(f"  [FAIL] {rel}")
        else:
            passed += 1
            print(f"  [OK]   {rel}")

    if failures:
        print(f"\n{'=' * 60}")
        print("  VALIDATION ERRORS")
        print("=" * 60)
        for name, errs in failures:
            print(f"\n  {name}:")
            for err in errs:
                print(f"    {err}")

    section("SUMMARY")
    print(f"\n  Passed : {passed}")
    print(f"  Failed : {failed}")
    print(f"  Total  : {passed + failed}")

    if failed:
        print("\n  [FAIL] One or more loot tables failed schema validation.")
        print("=" * 60)
        sys.exit(1)
    else:
        print("\n  [OK] All loot tables passed schema validation.")
        print("=" * 60)

    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()

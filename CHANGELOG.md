# Changelog

---

## [1.0.4] - 2026-07-05

### Fixed
- `dead_gold_pile_iron_golem` structure was so rare it could not be located even after searching millions of blocks. Reduced spacing (42 -> 20) and separation (23 -> 10) so it reliably generates within dead biomes.

---

## [1.0.3] - 2026-04-28

### Fixes
- Replaced blocks added in 1.21+ in several structures with 1.20-compatible equivalents

---

## [1.0.2] - 2026-04-27

### Fixes
- Resolved missing loot table for plainsandgrass_pine_cart
- Replaced invalid minecraft:bundle with minecraft:golden_apple in spruce_and_gold loot table
- fixed armor stand entity structures not spawning due to mismatched nbt filenames in template pool
- fixed desert_cart_1 spawning missing structure due to incorrect nbt reference in template pool

---

## [1.0.1] - 2026-03-23

### Update
- Ported to 1.20.x
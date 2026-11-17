# Changelog

---

## [1.0.6]

### Added
- Chests can hold maps that lead to gold piles and the big camps

### Fixed
- Chests that were meant to hold enchanted books, such as the abandoned house's, now give them instead of a blank book
- The golden helmet in the nether halls' chests now comes enchanted, as it does on newer versions
- The desert big house now has its armour stands
- Banners in the houses, item frames and the stable's chest now look right on Minecraft 1.20 to 1.20.4
- The gold piles' armour stands now keep their armour trims on Minecraft 1.20.5 and 1.20.6
- Tents, houses and other structures now spawn in all their biomes on Fabric and Forge
- Magic structures no longer generate on the Nether roof

### Changed
- Biomes O' Plenty is listed as a required dependency again on CurseForge and Modrinth
- Now requires Moog's Structure Lib 4.0.0 or newer

---

## [1.0.5] - 2026-07-07

### Fixed
- Fixed a mods.toml parse error that caused Minecraft to crash before launch on every 1.20.1 loader (Forge, NeoForge, Fabric). The mod description contains an apostrophe (`Biomes O' Plenty`), which was breaking the single-quoted TOML string in `mods.toml` and `neoforge.mods.toml`. Switched the affected placeholders to double quotes so the description parses correctly. Affected 1.0.4.

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
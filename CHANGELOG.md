# Changelog

---

## [1.0.9] - 2026-07-05

### Fixed
- `dead_gold_pile_iron_golem` structure was so rare it could not be located even after searching millions of blocks. Reduced spacing (42 -> 20) and separation (23 -> 10) so it reliably generates within dead biomes.

---

## [1.0.8] - 2026-07-04

### Changed
- mc 26.2 support

---

## [1.0.7] - 2026-05-25

_Pending. Update this header date and replace this line with the actual changes before tagging._

---

## [1.0.6] - 2026-05-25

### Fixed
- Fixed mods.toml parse error that prevented the mod from loading (`Invalid entry separator 'P' in inline table`). The mod description's apostrophe was breaking TOML string parsing.

---

## [1.0.5] - 2026-05-22

### Changed
- Rebalanced loot to address feedback that structures were too OP. Cut roll counts and stack sizes in the most common loot tables, reducing exposure of gold/iron/emerald/diamond by ~60-70%. Rare loot tables left untouched.
- `miners_camp_rare` chests no longer guarantee an enchanted diamond pickaxe in every chest (now ~22% chance).

### Fixed
- Versioned structures now have a defined path for Minecraft 26.1–26.1.2, so the game stops logging "no version mapping matched" warnings and no longer falls back to an older structure template.

---

## [1.0.4] - 2026-04-29

### Fixed
- Fixed structures failing to load when using moogs_structures 2.0.x
- Fixed some chests having broken loot tables that would produce no items
- Fixed `ruined_nether_fortress` loot that could fail to generate loot
- Fixed a `spruce_and_gold` loot table with incorrectly formatted loot

---

## [2.0.3] - 2026-04-27

### Fixed
- Resolved version compatibility issues where blocks used in structures were renamed or replaced between Minecraft versions

---

## [1.0.2] - 2026-04-27

### Fixed
- fixed armor stand entity structures not spawning due to mismatched nbt filenames in template pool

---

## [1.0.1] - 2026-03-31

### Added
- Added armour stand entity variants to structures

### Fixed
- Fixed NBT files for several large structures (big_pale_house_1, dead_big_house_1, desert_big_house_1, desert_house_5_bed, jungle_big_house_1, plainsandgrass_big_house_1)
- Removed yellow concrete from leafy column
- Restored canopy on palm log pile

### Changed
- Biomes o' Plenty is now a required dependency
- Updated mod icon

---

## [1.0.0] - 2026-03-29

### Added
- First release of Moog's Bountiful Structures for Minecraft 1.21
- Includes 96 structure groups and 142 structure NBT files spanning lots of BoP biomes including abandoned buildings, campsites, wells, log piles, towers, graveyards, and more

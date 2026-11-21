# Sky Select (Fabric, Minecraft 1.21.11)

In-game GUI (press **J** or run `/skyselect`) to pick one of several animated night skies.
Skies are rendered by **Skyboxify** (required at runtime) via OptiFine-format sky packs bundled in this mod.

| Preset | What you get |
|---|---|
| Northern Lights | two counter-rotating green→violet aurora curtains (shimmer) |
| Crimson Aurora | red/magenta aurora |
| Meteor Shower | stars + 3 layers of fast meteors |
| Polar Night | aurora **and** meteors |
| Cosmic Nebula | animated nebula, stars, a few meteors |
| [Debug] Layout Test | labelled cube faces, always visible |

## Build
1. Need JDK 21. Copy the Gradle wrapper from the Fabric example mod (or run `gradle wrapper`).
2. Check `gradle.properties` against https://fabricmc.net/develop (loader / Fabric API versions for 1.21.11).
3. `./gradlew build` -> `build/libs/skyselect-1.0.0.jar`
4. Put it in `mods/` together with Fabric API and Skyboxify.

## Regenerate / tweak skies
`python3 tools/gen_skies.py` (needs numpy + Pillow) rewrites `src/main/resources/resourcepacks/*`.
Aurora colours/heights, meteor counts/speeds, nebula colours are all in `main()`.

## How motion works
Skyboxify rotates each layer around an axis (`speed` = rotations per MC day).
* Aurora: two layers rotate in opposite directions around the vertical axis -> flowing, shimmering curtains.
* Meteors: streaks lie along circles around a tilted axis, layers spin at 97/131/163 rotations/day
  (~7-12 s per turn) so streaks sweep across the sky at different times. Integer speeds avoid a jump at day rollover.
* Layers are RGBA with `blend=alpha`, no fade times: they are visible day and night (clear weather only, OptiFine default).
  For night-only skies, call `write_props(..., fade=True)` in the generator (fades 19:00-20:00 in, 4:00-5:00 out).

## If something looks off
* **Meteors move tail-first** -> set `REVERSE_METEORS = True` in `tools/gen_skies.py`, regenerate.
* **Sky looks scrambled / seams** -> enable "[Debug] Layout Test" and compare labels to F3 facing.
* **Compile error on `Identifier`** -> your mappings use the old name `ResourceLocation`; swap the import.
* **Fabric API deprecation of `ResourceManagerHelper`** -> use `ResourceLoader.registerBuiltinPack` instead.

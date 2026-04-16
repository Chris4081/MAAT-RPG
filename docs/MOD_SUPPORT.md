# MAAT-RPG Mod Support

MAAT-RPG now supports a first external mod layer outside the game folder.

The important design rule is:

- mods live in the external app-support area
- not inside the repository or app bundle

## Mod Folder

The root mod folder is:

- macOS: `~/Library/Application Support/MAAT-RPG/mods`
- Linux: `~/.local/share/MAAT-RPG/mods`
- Windows: `%LOCALAPPDATA%\\MAAT-RPG\\mods`

Inside it, MAAT-RPG uses:

```text
mods/
  plugins/
  stories/
  battle_profiles/
```

## What Works in the Current First Version

### 1. External Plugin Mods

Put plugin folders or `plugin_*.py` files into:

```text
mods/plugins
```

They are loaded as an extra plugin root during MAAT-RPG startup.

### 2. Story Mods

Put story modules and config files into:

```text
mods/stories
```

Supported config files:

- `*.json`
- `*.yaml`
- `*.yml`

Expected structure:

```json
{
  "stories": [
    {
      "id": 101,
      "name": "A New Path",
      "module": "my_story",
      "music": "my_story_theme.mp3",
      "trigger": {
        "type": "message_count",
        "messages": 12,
        "position": "before"
      }
    }
  ]
}
```

The corresponding story module would be:

```text
mods/stories/my_story.py
```

It should provide a `Story` class, just like built-in story modules.

If a mod story uses the same `id` as a built-in story, it overrides that entry.

### 3. Battle Profile Mods

Put custom battle profiles into:

```text
mods/battle_profiles
```

Supported formats:

- `*.json`
- `*.yaml`
- `*.yml`

Minimal example:

```yaml
id: crystal_pharaoh
name: Crystal Pharaoh
fight_type: boss
description: A reflective crystal sovereign with stronger shatter pressure.
battle_profile:
  boss_name: Crystal Pharaoh
  intro_lines:
    - "A cold spectrum gathers around the arena."
  victory_lines:
    - "The crystal field breaks, but not its memory."
  enemy:
    hp_mult: 1.15
    damage_mult: 1.10
  boss_profile:
    title: Crystal of Fracture
    intro: Light bends until it becomes pressure.
    special: Prism Collapse
```

Start it in the game with:

```text
/fightmod crystal_pharaoh
```

List available battle mods with:

```text
/fightmod list
```

or:

```text
/mods
```

## Reward Behavior

Custom battle mods are safe by default:

- they run without persistent rewards unless explicitly enabled

If you want a modded battle to grant real rewards and progression, set:

```yaml
persistent_rewards: true
```

Use that carefully, because it affects balance.

## Relative Paths

For story and battle mod assets, relative paths are resolved relative to the mod file location.

That means this is valid:

```yaml
music:
  battle: music/my_mod_boss.mp3
```

as long as the file exists next to the mod package structure.

## Commands

Useful commands for the current mod system:

- `/mods`
- `/mod help`
- `/mod list`
- `/mod open`
- `/mod create battle <id>`
- `/mod create story <id>`
- `/mod create plugin <id>`
- `/fightmod list`
- `/fightmod <id>`

`/mod create ...` writes starter templates directly into the external mods folder:

- battle templates into `mods/battle_profiles`
- story templates into `mods/stories`
- plugin templates into `mods/plugins`

## Scope of the First Version

This first mod layer is intentionally focused on:

- external plugins
- story extension/override
- custom battle profiles

Future extensions could include:

- custom dungeon packs
- custom skill trees
- custom principle sets
- curated plugin marketplace support

# Contributing to MAAT-RPG

Thank you for contributing to MAAT-RPG.

This project mixes local AI infrastructure, game logic, and a modular plugin architecture. The most helpful contributions are the ones that improve the system without breaking profile safety, language support, or local-first behavior.

## Development Priorities

When contributing, please preserve these core principles:

- local-first execution
- bilingual German/English behavior where relevant
- profile-safe persistence outside the app bundle
- plugin modularity
- respectful, stable UX over flashy but fragile behavior

## Recommended Environment

Recommended Python versions:

- Python 3.11
- Python 3.12

Python 3.13 is currently not recommended because some dependencies may fail during installation.

## Setup

### Linux / macOS

```bash
git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG/maatos
bash setup.sh
```

### Windows

Windows support is currently experimental.

```powershell
git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG\maatos
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

For platform-specific notes, see:

- `README.md`
- `maatos/INSTALL_WINDOWS.md`
- `maatos/INSTALL_LINUX.md`

## Repository Orientation

Important top-level areas:

- `maatos/apps/maat_rpg`
  - RPG app code and app-specific plugins
- `maatos/shared`
  - shared MAAT runtime components and shared plugins
- `README.md`
  - user-facing overview
- `FUNKTIONEN.md`
  - feature overview

## Contribution Types

Good contributions include:

- gameplay fixes
- battle and quest balancing
- plugin stability improvements
- bilingual text fixes
- Linux/macOS/Windows compatibility improvements
- developer documentation
- safety and hallucination-guard improvements

## Coding Guidelines

### 1. Keep Runtime Data out of the Game Folder

Do not introduce new save or memory writes into the repository folder or app bundle.

Runtime data should go through the MAAT path helpers so it lands in the external app-support directory and remains profile-safe.

### 2. Preserve Bilingual Behavior

If a user-facing change is language-relevant, check both:

- German
- English

Avoid hardcoding German-only strings into English paths and vice versa.

### 3. Prefer Extending Plugins over Monolithic Core Changes

If a feature naturally belongs to:

- battle
- quests
- TTS
- memory
- dungeons
- achievements

try to keep the change inside the relevant plugin unless the core truly needs to change.

### 4. Respect Existing Save State

Be careful when changing:

- battle state
- quest state
- settings state
- memory schemas
- profile paths

If you migrate state, make the migration tolerant and preserve old installs where possible.

### 5. Keep Changes Honest

Please avoid:

- fake compatibility claims
- hardcoded assumptions presented as facts
- safety features that block too aggressively without good reason

MAAT-RPG values clarity and truthful behavior more than overconfident output.

## Plugin Contributions

Plugins should follow the established interface:

- `Plugin` class
- optional `type = "chat"` or `type = "stream"`
- lifecycle hooks such as `on_startup`, `before_chat`, `after_response`
- commands through `command(...)`, `commands`, or `available_commands`

See `docs/PLUGIN_API.md` for the detailed interface.

## Testing Checklist

Before opening a contribution, test the affected paths as practically as possible.

Recommended checks:

- app starts cleanly
- no plugin load errors
- German mode works
- English mode works
- profile-safe persistence still works
- no new writes appear in the game folder
- command help remains valid

If your change touches a gameplay system, also test the relevant live path:

- intro
- menu
- battle
- dungeon
- quests
- memory
- TTS

## Documentation Contributions

Documentation contributions are very welcome, especially for:

- architecture
- plugin development
- formulas and concepts
- installation and platform support

If you add a major feature, update the docs along with the code.

## Pull Request Guidance

A good contribution should explain:

- what changed
- why it changed
- what was tested
- whether the change affects saves, profiles, memory, or localization

If there are known limitations, state them openly.

## If You Are Unsure

If you are unsure whether a change belongs in:

- core runtime
- app plugin
- shared plugin
- documentation

start small, document your assumption, and prefer the less destructive change.

MAAT-RPG grows best through changes that are modular, transparent, and easy to reason about.

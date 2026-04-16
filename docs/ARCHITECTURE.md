# MAAT-RPG Architecture

This document explains how MAAT-RPG is composed internally and how the game, model runtime, and plugin system fit together.

## Overview

MAAT-RPG is built in layers:

1. Launcher and app selection
2. MAAT-RPG runtime shell
3. Shared model and streaming core
4. Plugin system
5. Profile-aware storage

At runtime, the system combines a local LLM, a terminal UI, and a plugin graph that can react before input, during streaming, and after each answer.

## Runtime Flow

The high-level startup path is:

1. `maatki.py` starts the selected app.
2. `shared/core/app_loader.py` calls the MAAT-RPG entrypoint.
3. `apps/maat_rpg/basic.py` prepares directories, profiles, model loading, commands, and plugins.
4. `PluginManager` loads app plugins and shared plugins.
5. `CommandRouter` registers system and plugin commands.
6. The chat loop begins and coordinates:
   - command handling
   - `before_chat` hooks
   - model generation
   - streaming hooks
   - `after_response` hooks
   - optional final-response guard hooks

## Main Components

### 1. Launcher Layer

The launcher chooses which MAAT app to run. For MAAT-RPG, the relevant entrypoint is the RPG runtime in `apps/maat_rpg/basic.py`.

### 2. MAAT-RPG Runtime Shell

`apps/maat_rpg/basic.py` is the central runtime shell. It is responsible for:

- preparing application directories
- selecting the active profile
- exporting profile-aware runtime paths through environment variables
- loading the model backend
- creating the command router
- loading plugins
- maintaining the conversation anchor and chat loop

This file is the bridge between the game layer and the shared MAAT-OS core.

### 3. Shared Core

The shared core provides reusable infrastructure:

- `shared/core/llm_loader.py`
  - model backend selection and loading
- `shared/core/streaming.py`
  - token streaming, console output, and stream plugin hooks
- `shared/core/command_router.py`
  - routing for `/commands`
- `shared/core/maat_paths.py`
  - profile-aware runtime directories
- `shared/core/plp_guard.py`
  - PLP-based hallucination-risk estimation

This shared layer keeps the RPG-specific code smaller and makes MAAT components reusable across apps.

## Plugin Architecture

Plugins are loaded from multiple plugin roots. In practice, MAAT-RPG combines:

- app-specific plugins under `apps/maat_rpg/plugins`
- shared plugins under `shared/plugins`

The loader ignores folders that start with `_` and expects either:

- a plugin folder with `plugin_main.py`
- or a direct `plugin_*.py` file

Each plugin is instantiated through a `Plugin` class and is classified as:

- `type = "chat"`
- `type = "stream"`

### Chat Plugins

Chat plugins participate in the turn lifecycle around a reply:

- `on_startup(context=None)`
- `before_chat(user_input, context=None)`
- `after_response(reply, context=None)`
- optionally `before_final_response(reply, context=None)`
- optionally `final_response_guard_enabled(context=None)`

Typical use cases:

- story triggers
- battles
- quests
- achievements
- memory updates
- profile-dependent game state

### Stream Plugins

Stream plugins can react while a reply is being streamed:

- `before_stream(text)`
- `on_token(token)`
- `after_stream(full_text)`

Typical use cases:

- TTS
- token-level display logic
- side-channel output processing

## Command Routing

Commands are handled by `shared/core/command_router.py`.

There are two command families:

- system commands registered directly on the router
- plugin commands registered by `PluginManager.register_plugin_commands(...)`

The execution order is:

1. system command
2. plugin command
3. unknown-command fallback

Any input beginning with `/` is treated as a command so the router can return a clean error message instead of silently ignoring it.

## Turn Processing Pipeline

A normal chat turn in MAAT-RPG looks like this:

1. User enters text.
2. Router checks whether the input is a command.
3. If it is normal chat, `before_chat` plugins run.
4. The model is called.
5. Stream plugins react during generation.
6. The full reply is collected.
7. `after_response` plugins can modify the reply.
8. If enabled, `before_final_response` plugins can guard or soften the final answer.
9. The final text is displayed and optionally spoken.

This structure lets the game layer and safety layer both influence the final output without tightly coupling everything into one file.

## Profiles and Persistence

MAAT-RPG is profile-aware.

The active profile determines the storage roots for:

- `data`
- `state`
- `saves`
- `logs`
- `cache`

Models remain shared so each profile does not need its own copy.

Important design rule:

- runtime state belongs in the external app-support area
- not in the app bundle or repository folder

This is especially important for:

- save data
- quest state
- battle state
- memory databases
- per-profile settings

## Game and Plugin Relationship

The RPG itself is not a monolithic game binary. It is better understood as a game shell plus plugins:

- `basic.py` provides the runtime frame
- plugins implement most gameplay systems

Examples:

- title/menu flow
- intro
- battle system
- dungeons
- quests
- achievements
- memory systems
- TTS
- uncertainty guard

That means extending the game usually means extending plugins rather than editing the core loop directly.

## Safety and Final Output Control

MAAT-RPG includes a PLP-based final response guard.

The guard can:

- allow a reply
- soften a reply
- block hard claims and replace them with a safer answer

This happens late in the pipeline through `before_final_response(...)`, which means:

- creativity can still happen
- but final claims can still be stabilized before display

## Design Intent

The architecture follows a few practical principles:

- local-first
- profile-safe persistence
- modular gameplay systems
- low coupling between game and model backend
- safety and reflection as layered systems, not hardcoded everywhere

In short:

MAAT-RPG is a plugin-driven terminal RPG running on top of a local MAAT-OS-style runtime, with profiles, modular game systems, and a final-response safety layer.

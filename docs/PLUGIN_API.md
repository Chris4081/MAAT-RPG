# MAAT-RPG Plugin API

This document explains the plugin interface used by MAAT-RPG and the shared MAAT runtime.

## Plugin Discovery

Plugins are loaded from configured plugin roots.

The loader supports:

- a folder containing `plugin_main.py`
- a direct `plugin_*.py` file

Folders beginning with `_` are ignored.

## Minimal Plugin Structure

A minimal plugin looks like this:

```python
class Plugin:
    type = "chat"
```

In practice, most plugins live in a folder like:

```text
my_plugin/
  plugin_main.py
```

## Plugin Types

Plugins can declare:

- `type = "chat"`
- `type = "stream"`

### Chat Plugins

Used for gameplay systems, commands, state changes, and response processing.

### Stream Plugins

Used for token-level behavior during generation, for example TTS.

## Supported Hooks

### `on_startup(context=None)`

Called after plugins are loaded.

Use it for:

- initialization
- startup checks
- optional setup actions
- menu or intro boot logic

Example:

```python
def on_startup(self, context=None):
    pass
```

### `before_chat(user_input, context=None)`

Called before the model is queried.

Typical use cases:

- story triggers
- battle triggers
- input rewriting
- quest progression
- memory capture

Valid return styles:

- `(False, None)` -> not handled, continue normally
- `(False, new_input)` -> continue with modified input
- `(True, output)` -> handled; stop normal flow and use `output`
- `str` -> replace input text

### `after_response(reply, context=None)`

Called after a full reply has been generated.

Typical use cases:

- append HUD or logs
- update state
- soften formatting
- store memories

Valid return styles:

- `None` -> leave reply unchanged
- `str` -> replace reply

### `before_final_response(reply, context=None)`

Optional late-stage guard hook.

This is intended for final stabilization after normal post-processing.

Typical use cases:

- hallucination risk mitigation
- cautionary rewording
- blocking hard claims when confidence is too low

Valid return styles:

- `None` -> keep current reply
- `str` -> replace final reply

### `final_response_guard_enabled(context=None)`

Optional companion hook for `before_final_response(...)`.

Use this when a final-response guard should only activate under certain conditions, such as a user setting.

Return:

- `True` -> guard is active
- `False` -> guard is inactive

## Stream Hooks

These hooks are relevant for `type = "stream"` plugins.

### `before_stream(text)`

Called before streaming output begins.

### `on_token(token)`

Called for each streamed token or chunk.

### `after_stream(full_text)`

Called after streaming finishes.

Typical use case:

- text-to-speech

## Commands

There are three main ways to expose plugin commands.

### 1. `command(cmd, context=None)`

General command handler.

Example:

```python
def command(self, cmd, context=None):
    if cmd == "/mycmd":
        return "Hello"
    return None
```

Possible return styles:

- `None` -> not handled
- `str` -> immediate output
- `(True, reply)` -> explicitly handled

### 2. `commands = {...}`

Dictionary-based registration.

Example:

```python
commands = {
    "/mycmd": {"de": "Mein Befehl", "en": "My command"}
}
```

This lets the plugin manager register commands directly on the router with descriptions.

### 3. `available_commands = [...]`

List-based registration.

Example:

```python
available_commands = ["/mycmd", "/mycmd info"]
```

If a plugin exposes `command(...)` but no explicit command list, the loader can also register a fallback command name.

## Context Object

Many hooks receive a `context` dictionary.

Depending on the runtime stage, it may contain things like:

- `conversation`
- `last_user_input`
- `pm`
- battle or story state references
- MAAT meta information
- profile-related state

Plugins should treat context keys defensively:

- check whether a key exists
- do not assume every context is complete

## Best Practices

### Keep Plugins Focused

A plugin should usually own one responsibility:

- quests
- battle
- memory
- TTS
- uncertainty guard

This keeps debugging and maintenance manageable.

### Be Tolerant About Signatures

Older plugins may still exist in the ecosystem. The loader already tries to tolerate some older call signatures, so new plugins should prefer the modern `(value, context=None)` style without breaking old installs unnecessarily.

### Use Shared Path Helpers

If your plugin stores runtime state, use the MAAT path helpers so data lands in the active external profile path, not in the repository folder or app bundle.

### Handle Both Languages

If your plugin prints user-facing text, support:

- German
- English

### Avoid Hard Failures in Hooks

Hooks should fail softly whenever possible. A plugin should not bring down the entire game because a non-critical side action failed.

## Example Chat Plugin

```python
class Plugin:
    type = "chat"

    commands = {
        "/echo": {"de": "Echo ausgeben", "en": "Print echo"}
    }

    def on_startup(self, context=None):
        pass

    def command(self, cmd, context=None):
        if cmd.startswith("/echo "):
            return cmd[6:]
        return None

    def before_chat(self, user_input, context=None):
        return False, None

    def after_response(self, reply, context=None):
        return reply
```

## Example Stream Plugin

```python
class Plugin:
    type = "stream"

    def before_stream(self, text):
        pass

    def on_token(self, token):
        pass

    def after_stream(self, full_text):
        pass
```

## Related Files

If you want to inspect the runtime behavior directly, the most relevant source files are:

- `shared/plugins/plugin_loader.py`
- `shared/core/command_router.py`
- `shared/core/streaming.py`
- `apps/maat_rpg/basic.py`

Together, these files define how plugins are discovered, called, and integrated into the MAAT-RPG turn loop.

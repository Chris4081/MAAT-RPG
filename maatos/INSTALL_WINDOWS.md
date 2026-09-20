# Windows Installation

MAAT-RPG has **experimental Windows support**.

Recommended:
- Windows 10/11
- PowerShell
- Python **3.11** or **3.12**
- `cmake`
- Visual Studio Build Tools for `llama-cpp-python`
- `ffmpeg` / `ffplay` for music

## Quick Start

```powershell
git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG\maatos
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

After the first setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

## Notes

- Persistent data is stored outside the game folder in the Windows app-support path:
  - usually `%LOCALAPPDATA%\MAAT-RPG`
- TTS uses PowerShell + `System.Speech`
- Music currently works best when `ffplay` is installed
- Python 3.13 is **not recommended**

## Current Scope

Windows support is still experimental.

The following groundwork is already covered:
- Windows app-support paths
- PowerShell setup and start scripts
- Windows TTS fallback
- safer terminal fallbacks where `termios` is unavailable

The most likely remaining rough edges are terminal-specific behaviors and platform-specific audio details.

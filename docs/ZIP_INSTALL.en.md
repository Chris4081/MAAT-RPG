# MAAT RPG with music – download, set up and play

**English** · [Deutsch](ZIP_INSTALL.de.md) · [Back to README](../README.md)

[**🎵 Download MAAT RPG with music (.zip)**](https://maat-research.com/data/downloads/maat-rpg.zip)

The ZIP contains the game source code, artwork, background music and original
sound effects. You set up Python, the required libraries and the AI backend once
on your own computer. Choose your own GGUF model afterwards; no AI model is included.

**Steps:** download → extract → set up once → choose a model → play.
You do not need to repeat installation for each game session.


> Automatic setup applies to the updated ZIP containing `Install.command` and
> `SETUP.md`. If the server download does not contain them yet, use the manual
> steps in [GUI-START.md](../GUI-START.md#english) for that older archive.

## 1. Download and extract everything

1. Download the ZIP using the link above and wait for it to finish.
2. Extract the entire archive into its own folder, for example **MAAT-RPG** in
   Documents. On Windows, right-click the ZIP and select **Extract All**; on macOS,
   double-click it; on Linux, use your file manager's extraction option.
3. Open the extracted game folder. It should contain:

```text
MAAT-RPG/
├── Install.command
├── setup.sh
├── SETUP.md
├── start_gui.py
├── requirements-gui.txt
├── Start GUI.command
├── Install Linux.sh
├── Start Linux.sh
├── maatos/
└── packaging/
```

If another folder appears first, open it until you reach `start_gui.py`.
Keep all subfolders together. Use a local drive and keep the game folder in the
same location after setup.

Open a terminal **inside this game folder**. On macOS, type `cd ` with a trailing
space, drag the folder from Finder into Terminal, then press Enter. Linux file
managers often offer **Open in Terminal**; on Windows, use **Open in Terminal**
and select PowerShell.

Continue with your system: [macOS](#2-macos--intel-and-apple-silicon) ·
[Linux](#3-linux--ubuntu-mint-and-debian) · [Windows](#4-windows--experimental).

## 2. macOS – Intel and Apple Silicon

Requires **macOS 13.3 or newer**. Double-click **Install.command** in the extracted
game folder. Setup installs native Python if needed, the GUI, build tools and
the appropriate GGUF backend automatically.

Enter your administrator password or complete Apple's Command Line Tools dialog
if requested. Keep the terminal open: after successful setup, the game starts
automatically. Select your own GGUF model in the game.

Later launches: double-click **Start GUI.command**. If Finder cannot start the
file, run `bash Install.command` or `bash "Start GUI.command"` in the game folder.

Apple Silicon uses Metal; Intel uses CPU acceleration with Apple Accelerate.
[Setup options, prerequisites and help](../SETUP.md#english).

## 3. Linux – Ubuntu, Mint and Debian

Open a terminal in the extracted game folder and run **without sudo**:

```bash
bash setup.sh
```

Setup installs system packages through your distribution's package manager;
enter your administrator password if requested. It then sets up the GUI and
native CPU backend, adds a menu entry and starts the game. Fedora, Arch and
openSUSE are also detected. A 64-bit graphical desktop and the Python/glibc
versions listed in the [Linux guide](INSTALL_LINUX.md#english) are required.

Later launches: select **MAAT RPG** in the applications menu or run
`bash "Start Linux.sh"`. To install without launching: `bash setup.sh --no-start`.
On older CPUs, the first backend build can take several minutes.

## 4. Windows – experimental

This launch path is provided but has not been validated on Windows for this ZIP
edition. Install 64-bit Python 3.11/3.12 and Visual Studio C++ Build Tools with a
Windows SDK. Use PowerShell with the C++ build environment available, such as
Visual Studio's Developer PowerShell.

Inside the extracted game folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m pip install cmake ninja
$env:CMAKE_ARGS = "-DGGML_NATIVE=ON -DGGML_METAL=OFF -DLLAMA_CURL=OFF"
.\.venv\Scripts\python.exe -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
.\.venv\Scripts\python.exe start_gui.py
```

For Python 3.11, replace only `py -3.12` with `py -3.11`. For later sessions,
run this from the game folder:

```powershell
.\.venv\Scripts\python.exe start_gui.py
```

These commands do not require activating the environment in PowerShell.

## 5. First game session

If you do not have a model yet, download a suitable Chat/Instruct GGUF from a
model source of your choice. Check its license and RAM requirements there and
keep it in a permanent folder. The game uses the file ending in `.gguf`;
the game ZIP does not supply that model file.

1. Choose a game language and profile when prompted.
2. Open **AI & Models** or **Choose model from file …**.
3. Select an existing **Chat/Instruct GGUF file** and choose **Load model**.
   See the [supported model families](../README.md#supported-ai-models).
4. Leave loading settings on **Auto · Default** initially. The default context is
   20,000 tokens. Model size, quantization and context must fit available RAM;
   start with a small model on older hardware.
5. Wait for loading to finish and **PRESS ENTER TO PLAY** to appear.
   Start your journey, experience the intro and write your first message.

Model selection is saved per profile. Keep the GGUF file in the same location
so the game can find it at the next start.

## 6. Music and speech

The music files are already included in this ZIP. The initial language-choice
screen is silent; music begins on the title screen.

If you hear nothing, open **Settings → Music & Sound**:

- Enable **Music in menus, stories and battles**.
- Set the volume above zero and choose an available audio output.
- **Sound effects and level-ups** has its own switch.

An existing profile may retain a previous “music off” setting. Text-to-speech is
enabled separately in the dialogue/speech settings.

## 7. Saves, updates and help

Profiles and saves are stored outside the extracted game folder by default:

| System | Data folder |
| --- | --- |
| macOS | `~/Library/Application Support/MAAT-RPG/` |
| Linux | `~/.local/share/MAAT-RPG/`, or under `XDG_DATA_HOME` |
| Windows | `%LOCALAPPDATA%\MAAT-RPG\`, falling back to `%APPDATA%\MAAT-RPG\` |

Custom data-path settings can change these locations. Back up your data folder
before updating. Extract a new edition into its own folder and set up its
environment again; your existing profiles appear when the data paths stay the same.

| Message or problem | What to do |
| --- | --- |
| Cannot find `start_gui.py` or `requirements-gui.txt` | Extract the complete ZIP and open the correct game folder. |
| `No module named PySide6` | Use the game's `.venv` and run `python -m pip install -r requirements-gui.txt`; on Windows use the full `.venv\Scripts\python.exe` path. On Linux rerun the Linux installer. |
| AI backend / `llama_cpp` missing | Complete the backend-installation step for your operating system above. |
| CMake or compiler error | Check the Command Line Tools, Linux build packages or Windows C++ build environment. |
| Model cannot load or replies take a long time | Use Auto settings, close other memory-heavy programs and try a smaller GGUF or context. |
| No sound | Check the music switch, volume and audio device; existing profile preferences are preserved. |

For troubleshooting, launch from a terminal and keep the final error messages.
Diagnostic logs are also stored in the data folder's `logs/` subfolder. Include
your operating system, CPU/RAM, model filename and reproduction steps in bug reports;
remove private conversation content before sharing logs.

[Download choices](../README.md#download-and-play) ·
[General GUI guide](../GUI-START.md#english) ·
[Music and sound effects](MUSIC.md#english)

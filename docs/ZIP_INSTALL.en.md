# MAAT RPG with music – download, set up and play

**English** · [Deutsch](ZIP_INSTALL.de.md) · [Back to README](../README.md)

[**🎵 Download MAAT RPG with music (.zip)**](https://maat-research.com/data/downloads/maat-rpg.zip)

The ZIP contains the game source code, artwork, background music and original
sound effects. You set up Python, the required libraries and the AI backend once
on your own computer. Choose your own GGUF model afterwards; no AI model is included.

**Steps:** download → extract → set up once → choose a model → play.
You do not need to repeat installation for each game session.

## 1. Download and extract everything

1. Download the ZIP using the link above and wait for it to finish.
2. Extract the entire archive into its own folder, for example **MAAT-RPG** in
   Documents. On Windows, right-click the ZIP and select **Extract All**; on macOS,
   double-click it; on Linux, use your file manager's extraction option.
3. Open the extracted game folder. It should contain:

```text
MAAT-RPG/
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

### Requirements and processor type

- **macOS 13.3 or later** for the GUI used here.
- Native **64-bit Python 3.11 or 3.12**. The examples use Python 3.12;
  replace `python3.12` with `python3.11` if that is your installed version.
- Internet access during setup and Apple's Command Line Tools to build the backend.

**Apple menu → About This Mac** identifies your Intel processor or Apple chip,
such as M1, M2, M3 or M4. Apple chips use the ARM variant. Use native Python on
Apple Silicon so the backend can use Metal.

If the Command Line Tools are missing, install them and wait for completion:

```bash
xcode-select --install
```

If they are already installed, continue.
[Apple's instructions](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools).

Check Python:

```bash
python3.12 --version
```

If you use Homebrew, install Python 3.12 with `brew install python@3.12`, then
open a new terminal. See the [Homebrew formula](https://formulae.brew.sh/formula/python@3.12).
Install Homebrew itself using its [official instructions](https://brew.sh/);
your macOS version must be supported by Homebrew. An existing suitable Python
installation also works.

### Set up the game environment once

Run these commands one after another inside the extracted game folder:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt
python -m pip install cmake ninja
```

The `.venv` environment belongs to this copy of the game. Keep this terminal open.
Now run **exactly one** of the following backend commands, matching your Mac:

**Apple Silicon – ARM and Metal:**

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=ON -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

**Intel Mac – CPU and Apple Accelerate:**

```bash
CMAKE_ARGS="-DGGML_NATIVE=ON -DGGML_METAL=OFF -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF" CMAKE_BUILD_PARALLEL_LEVEL=4 python -m pip install --no-binary=llama-cpp-python llama-cpp-python==0.3.34
```

The AI backend is compiled for your computer. This can take several minutes;
wait for the command to finish successfully. Set up a new environment on each
computer instead of transferring a compiled `.venv` between machines.

### Launch

In the same terminal:

```bash
python start_gui.py
```

For later sessions, open a terminal in the game folder and run:

```bash
source .venv/bin/activate
python start_gui.py
```

After setup, **Start GUI.command** also detects `.venv`. If double-clicking does
not launch it, run the script from the terminal:

```bash
bash "Start GUI.command"
```

## 3. Linux – Ubuntu, Mint and Debian

Use a 64-bit system with a graphical desktop. Ubuntu 22.04/24.04 are suitable
starting points for Intel/AMD. The ARM64 Qt packages require glibc 2.39, as in
Ubuntu 24.04. Python 3.11/3.12 is recommended; the Linux installer supports
Python 3.10–3.13.

Install the system packages once:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-dev build-essential cmake pkg-config \
  libopenblas-dev libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0 \
  libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 \
  libxcb-xinerama0 libxcb-xkb1 libx11-xcb1 libdbus-1-3 libpulse0 \
  ffmpeg speech-dispatcher espeak-ng fonts-dejavu-core fonts-noto-color-emoji
```

Then, inside the extracted game folder, run **without sudo**:

```bash
bash "Install Linux.sh"
```

The installer creates a Python environment, installs GUI libraries, builds the
CPU backend for your machine and adds a **MAAT RPG** application-menu entry.
Wait for it to finish successfully; the build can take longer on older computers.

Start the game:

```bash
bash "Start Linux.sh"
```

For later sessions, use that same start command or the **MAAT RPG** menu entry.
You do not need to reinstall. The menu entry points to your extracted game folder,
so keep that folder in its original location.

For other distributions, display the relevant package commands:

```bash
bash "Install Linux.sh" --system-deps
```

See the [Linux guide](INSTALL_LINUX.md#english) for other configurations, Python
selection and backend repair. This Linux edition runs AI inference on the CPU;
it does not automatically use an arbitrary graphics card.

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

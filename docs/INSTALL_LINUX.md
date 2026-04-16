# MAAT-RPG on Linux

## What works

- Main game and chat loop
- Local `llama.cpp` backend
- Audio via `ffplay`, `mpg123`, or `aplay`
- Memory v5/v6 with NumPy fallback when FAISS is missing

## What is optional

- `faiss-cpu` is optional
- Linux TTS works best with `spd-say`, otherwise `espeak-ng` or `espeak`
- `mlx` is ignored on Linux and on Intel Macs

## Quick install

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential cmake ffmpeg mpg123 alsa-utils speech-dispatcher espeak-ng
git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG
bash setup.sh
```

### Fedora

```bash
sudo dnf install -y python3 python3-pip gcc gcc-c++ make cmake ffmpeg mpg123 alsa-utils speech-dispatcher espeak-ng
git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG
bash setup.sh
```

### Arch

```bash
sudo pacman -Sy --needed python python-pip base-devel cmake ffmpeg mpg123 alsa-utils speech-dispatcher espeak-ng
git clone https://github.com/Chris4081/MAAT-RPG.git
cd MAAT-RPG
bash setup.sh
```

## Data path

- With `XDG_DATA_HOME`: `$XDG_DATA_HOME/MAAT-RPG`
- Otherwise: `~/.local/share/MAAT-RPG`

## Notes

- `setup.sh` automatically prefers `python3.12`, then `python3.11`, then `python3`.
- If your system defaults to Python 3.13, use:

```bash
MAAT_SETUP_PYTHON=python3.11 bash setup.sh
```

- `ffplay` is the preferred Linux audio backend.
- If `ffplay` is missing, MAAT-RPG tries `mpg123`, then `aplay`.
- For TTS, MAAT-RPG prefers `spd-say`, then `espeak-ng`, then `espeak`.
- If `faiss-cpu` cannot be installed, MAAT-RPG still runs with the built-in NumPy vector fallback.

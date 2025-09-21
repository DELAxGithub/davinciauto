import os
import pathlib
import sys

HOME = pathlib.Path.home()
APP_SUPPORT = HOME / "Library" / "Application Support" / "davinciauto-cli"
CACHE_DIR = APP_SUPPORT / "cache"
TMP_DIR = APP_SUPPORT / "tmp"
for directory in (APP_SUPPORT, CACHE_DIR, TMP_DIR):
    directory.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))
os.environ.setdefault("PYTHONPYCACHEPREFIX", str(CACHE_DIR / "pyc"))
os.environ.setdefault("TMPDIR", str(TMP_DIR))

meipass = getattr(sys, "_MEIPASS", None)
if meipass:
    bin_dir = pathlib.Path(meipass) / "bin"
    bin_dir_str = str(bin_dir)
    if "DAVA_FFMPEG_PATH" not in os.environ:
        ffmpeg_candidate = bin_dir / "ffmpeg"
        if ffmpeg_candidate.exists():
            os.environ["DAVA_FFMPEG_PATH"] = str(ffmpeg_candidate)
            os.environ.setdefault("DAVINCIAUTO_FFMPEG", str(ffmpeg_candidate))
    if "DAVA_FFPROBE_PATH" not in os.environ:
        ffprobe_candidate = bin_dir / "ffprobe"
        if ffprobe_candidate.exists():
            os.environ["DAVA_FFPROBE_PATH"] = str(ffprobe_candidate)
            os.environ.setdefault("DAVINCIAUTO_FFPROBE", str(ffprobe_candidate))
    current_path = os.environ.get("PATH", "")
    if bin_dir_str not in current_path.split(os.pathsep):
        os.environ["PATH"] = bin_dir_str + os.pathsep + current_path if current_path else bin_dir_str

version_paths = []
if meipass:
    version_paths.append(pathlib.Path(meipass) / "VERSION")
try:
    version_paths.append(pathlib.Path(sys.argv[0]).resolve().parent / "VERSION")
except Exception:
    pass
for candidate in version_paths:
    if candidate.exists():
        value = candidate.read_text(encoding="utf-8").strip()
        if value:
            os.environ.setdefault("DAVINCIAUTO_CLI_VERSION", value)
            break

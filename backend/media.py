"""דחיסת אודיו — קבצי WAV/FLAC מ-NotebookLM הופכים ל-M4A קטן.

פרק של 15 דקות ב-WAV שוקל ~150MB; ב-AAC מונו 64k הוא ~7MB.
זה חוסך מקום בדיסק של המק מיני ונטען מהר בטלפון.
אם ffmpeg לא מותקן — הקובץ נשמר כמו שהוא.
"""
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("tact-news")

TRANSCODE_EXTS = (".wav", ".flac", ".aif", ".aiff")


def maybe_transcode(src: Path, name: str) -> tuple[Path, str]:
    """מחזיר (קובץ, שם) — אחרי דחיסה אם צריך, אחרת את המקור."""
    if Path(name).suffix.lower() not in TRANSCODE_EXTS or not shutil.which("ffmpeg"):
        return src, name
    out = src.with_name(src.name + ".m4a")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
           "-vn", "-ac", "1", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(out)]
    try:
        subprocess.run(cmd, check=True, timeout=900, capture_output=True)
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning("דחיסת %s נכשלה, נשמר המקור: %s", name, e)
        out.unlink(missing_ok=True)
        return src, name
    src.unlink(missing_ok=True)
    return out, str(Path(name).with_suffix(".m4a"))

"""
ClipDL - convertisseur local YouTube / Twitch / TikTok -> MP4 / MP3
Usage perso. Aucun compte ni clé API : tout passe par yt-dlp + FFmpeg.
Lancement : python app.py  (ou ClipDL.exe une fois compilé)
"""
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file
import yt_dlp

# --------------------------------------------------------------------------- #
# Chemins : fonctionne en script ET en .exe PyInstaller (sys._MEIPASS)
# --------------------------------------------------------------------------- #
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DOWNLOAD_DIR = Path.home() / "Downloads" / "ClipDL"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_HOSTS = re.compile(
    r"^https?://([a-z0-9-]+\.)*(youtube\.com|youtu\.be|twitch\.tv|tiktok\.com)(/|$)",
    re.IGNORECASE,
)


def find_ffmpeg() -> str | None:
    """FFmpeg du PATH en priorité, sinon celui embarqué par imageio-ffmpeg."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG = find_ffmpeg()
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
jobs: dict[str, dict] = {}


# --------------------------------------------------------------------------- #
# Téléchargement
# --------------------------------------------------------------------------- #
def build_options(job_id: str, fmt: str, quality: str) -> dict:
    def hook(d):
        job = jobs[job_id]
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            job["progress"] = round(done / total * 100, 1) if total else job["progress"]
            job["speed"] = d.get("_speed_str", "").strip()
            job["eta"] = d.get("_eta_str", "").strip()
            job["status"] = "downloading"
        elif d["status"] == "finished":
            job["status"] = "converting"
            job["progress"] = 100

    def pp_hook(d):
        if d["status"] == "finished":
            path = d.get("info_dict", {}).get("filepath")
            if path:
                jobs[job_id]["file"] = path

    opts = {
        "outtmpl": str(DOWNLOAD_DIR / "%(title).150B [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "postprocessor_hooks": [pp_hook],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if FFMPEG:
        opts["ffmpeg_location"] = FFMPEG

    if fmt == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": quality if quality in {"128", "192", "320"} else "192",
        }]
    else:
        h = f"[height<={quality}]" if quality.isdigit() else ""
        # H.264 + AAC en priorité = MP4 lisible partout (lecteur Windows, téléphone...)
        opts["format"] = (
            f"bv*{h}[vcodec^=avc1]+ba[acodec^=mp4a]/"
            f"bv*{h}+ba/b{h}/bv*+ba/b"
        )
        opts["merge_output_format"] = "mp4"
        opts["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]
    return opts


def run_job(job_id: str, url: str, fmt: str, quality: str):
    job = jobs[job_id]
    try:
        with yt_dlp.YoutubeDL(build_options(job_id, fmt, quality)) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("is_live"):
                raise ValueError("Les lives en cours ne sont pas pris en charge (attends la VOD).")
            job["title"] = info.get("title", "")
            job["thumbnail"] = info.get("thumbnail", "")
            info = ydl.process_ie_result(info, download=True)
            if not job.get("file"):
                path = Path(ydl.prepare_filename(info))
                job["file"] = str(path.with_suffix(".mp3" if fmt == "mp3" else ".mp4"))
        if not Path(job["file"]).exists():
            raise FileNotFoundError("Fichier final introuvable après conversion.")
        job.update(status="done", progress=100, filename=Path(job["file"]).name)
    except Exception as e:
        msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e))  # retire les codes couleur
        job.update(status="error", error=msg)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return render_template("index.html", ffmpeg=bool(FFMPEG),
                           folder=str(DOWNLOAD_DIR), version=yt_dlp.version.__version__)


@app.post("/api/download")
def api_download():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    fmt = data.get("format", "mp4")
    quality = str(data.get("quality", "best"))
    if not ALLOWED_HOSTS.match(url):
        return jsonify(error="Lien non reconnu (YouTube, Twitch ou TikTok uniquement)."), 400
    if fmt not in ("mp4", "mp3"):
        return jsonify(error="Format invalide."), 400
    if not FFMPEG:
        return jsonify(error="FFmpeg introuvable : installe-le ou ajoute-le au PATH."), 500
    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = {"status": "queued", "progress": 0, "format": fmt, "created": time.time()}
    threading.Thread(target=run_job, args=(job_id, url, fmt, quality), daemon=True).start()
    return jsonify(id=job_id)


@app.get("/api/progress/<job_id>")
def api_progress(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify(error="Tâche inconnue"), 404
    return jsonify({k: v for k, v in job.items() if k != "file"})


@app.get("/api/file/<job_id>")
def api_file(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        return jsonify(error="Fichier pas prêt"), 404
    return send_file(job["file"], as_attachment=True, download_name=job["filename"])


@app.post("/api/open-folder")
def api_open_folder():
    if sys.platform.startswith("win"):
        os.startfile(DOWNLOAD_DIR)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", DOWNLOAD_DIR])
    else:
        subprocess.Popen(["xdg-open", DOWNLOAD_DIR])
    return jsonify(ok=True)


# --------------------------------------------------------------------------- #
def free_port(preferred=5055) -> int:
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"ClipDL lancé sur {url}")
    print(f"Fichiers enregistrés dans : {DOWNLOAD_DIR}")
    print(f"FFmpeg : {FFMPEG or 'INTROUVABLE'}")
    print("Ferme cette fenêtre pour arrêter l'application.")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    # 127.0.0.1 = accessible uniquement depuis ton PC
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)

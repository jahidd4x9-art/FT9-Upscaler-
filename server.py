import os
import uuid
import subprocess
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"

UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="Free Video Upscaler")

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


PRESETS = {
    "1080_60": {
        "width": 1080,
        "height": 1920,
        "fps": 60
    },
    "2k_90": {
        "width": 1440,
        "height": 2560,
        "fps": 90
    },
    "4k_120": {
        "width": 2160,
        "height": 3840,
        "fps": 120
    }
}


@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/process")
async def process_video(
    video: UploadFile = File(...),
    preset: str = Form(...)
):

    if preset not in PRESETS:
        return {"error": "Invalid preset"}

    data = await video.read()

    job_id = uuid.uuid4().hex

    input_file = UPLOADS / f"{job_id}_{video.filename}"
    output_file = OUTPUTS / f"{job_id}.mp4"

    input_file.write_bytes(data)

    p = PRESETS[preset]

    width = p["width"]
    height = p["height"]
    fps = p["fps"]

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),

        "-vf",
        f"scale={width}:{height}:flags=lanczos,"
        f"fps={fps}",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",

        "-c:a", "aac",
        "-b:a", "192k",

        "-movflags", "+faststart",

        str(output_file)
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return {
                "error": "FFmpeg processing failed",
                "details": result.stderr[-2000:]
            }

        return {
            "success": True,
            "download": f"/download/{output_file.name}"
        }

    finally:
        try:
            input_file.unlink()
        except:
            pass


@app.get("/download/{filename}")
async def download(filename: str):

    file_path = OUTPUTS / filename

    if not file_path.exists():
        return {"error": "File not found"}

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename="upscaled_video.mp4"
    )

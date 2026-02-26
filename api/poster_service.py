"""MapGen — Background poster generation service using ThreadPoolExecutor."""

import uuid
from concurrent.futures import ThreadPoolExecutor

from engine.renderer import render_poster

executor = ThreadPoolExecutor(max_workers=4)

# In-memory job tracking: {job_id: {status, output_file, error}}
jobs: dict[str, dict] = {}


def submit_job(
    location: str,
    theme: str = "37th_parallel",
    size: str = "16x20",
    crop: str = "full",
    detail_layers: bool = True,
    distance: int | None = None,
    pin_lat: float | None = None,
    pin_lon: float | None = None,
    pin_style: int = 1,
    pin_color: str | None = None,
    font_preset: int = 1,
    text_line_1: str | None = None,
    text_line_2: str | None = None,
    text_line_3: str | None = None,
    dpi: int = 300,
    border: bool = False,
) -> str:
    """Submit a poster generation job and return a job_id."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "output_file": None, "error": None}

    def run():
        try:
            output_file = render_poster(
                location=location,
                theme=theme,
                size=size,
                crop=crop,
                detail_layers=detail_layers,
                distance=distance,
                pin_lat=pin_lat,
                pin_lon=pin_lon,
                pin_style=pin_style,
                pin_color=pin_color,
                font_preset=font_preset,
                text_line_1=text_line_1,
                text_line_2=text_line_2,
                text_line_3=text_line_3,
                dpi=dpi,
                border=border,
            )
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["output_file"] = output_file
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    executor.submit(run)
    return job_id


def get_job(job_id: str) -> dict | None:
    """Return job status dict or None if not found."""
    return jobs.get(job_id)

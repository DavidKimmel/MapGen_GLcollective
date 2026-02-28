"""MapGen — Flask API routes for the web frontend."""

import json
import os

from flask import Blueprint, jsonify, request, send_file

from api.poster_service import get_job, submit_job
from engine.renderer import get_available_themes, THEMES_DIR, FILE_ENCODING, GELATO_DIR
from export.gelato_export import export_for_gelato
from utils.geocoding import geocode_search

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/geocode")
def geocode():
    """Search for cities via Nominatim. Returns top 5 results."""
    q = request.args.get("q", "").strip()
    results = geocode_search(q, limit=5)
    return jsonify(results)


@api.route("/themes")
def themes():
    """List all available themes with full color palettes."""
    return jsonify(get_available_themes())


@api.route("/generate", methods=["POST"])
def generate():
    """Submit a poster generation job. Returns job_id."""
    body = request.get_json(force=True)

    required = ["city", "lat", "lon"]
    for field in required:
        if field not in body:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Build location string
    location = f"{body['lat']},{body['lon']}"

    job_id = submit_job(
        location=location,
        theme=body.get("theme", "37th_parallel"),
        size=body.get("size", "16x20"),
        crop=body.get("crop", "full"),
        detail_layers=bool(body.get("detail_layers", True)),
        distance=int(body["distance"]) if body.get("distance") else None,
        pin_lat=float(body["pin_lat"]) if body.get("pin_lat") is not None else None,
        pin_lon=float(body["pin_lon"]) if body.get("pin_lon") is not None else None,
        pin_style=int(body.get("pin_style", 1)),
        pin_color=body.get("pin_color"),
        font_preset=int(body.get("font_preset", 1)),
        text_line_1=body.get("text_line_1") or body.get("city"),
        text_line_2=body.get("text_line_2") or body.get("country"),
        text_line_3=body.get("text_line_3"),
        dpi=int(body.get("dpi", 300)),
        border=bool(body.get("border", False)),
    )
    return jsonify({"job_id": job_id})


@api.route("/status/<job_id>")
def status(job_id):
    """Poll job status."""
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@api.route("/download/<job_id>")
def download(job_id):
    """Download completed poster file."""
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "complete":
        return jsonify({"error": "Job not complete"}), 400

    filepath = job["output_file"]
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    return send_file(filepath, as_attachment=True)



@api.route("/gelato-export/<job_id>", methods=["POST"])
def gelato_export(job_id):
    """Trigger Gelato export for a completed job."""
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "complete":
        return jsonify({"error": "Job not complete"}), 400

    filepath = job["output_file"]
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Source file not found"}), 404

    body = request.get_json(force=True) if request.is_json else {}
    sizes = body.get("sizes") or [job["size"]]
    bg_color = body.get("bg_color", "#F5F2ED")

    try:
        results = export_for_gelato(filepath, GELATO_DIR, sizes, bg_color)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

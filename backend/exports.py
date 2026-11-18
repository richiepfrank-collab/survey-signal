"""Exports: GeoJSON, KML, and an HTML survey-assist report."""
from __future__ import annotations

import datetime as _dt
import json
from xml.sax.saxutils import escape

from jinja2 import Template

DISCLAIMER = (
    "SURVEY-ASSIST OUTPUT ONLY. This map marks AI-flagged, human-reviewed candidate surface "
    "objects. It is NOT a clearance document, does NOT indicate that unmarked areas are safe, "
    "and must only be used by accredited mine action operators as an input to IMAS-compliant "
    "survey. Detects surface-laid objects only; buried hazards are not represented."
)


def to_geojson(detections: list[dict], statuses=("confirmed",)) -> dict:
    feats = []
    for d in detections:
        if d["status"] not in statuses or d.get("lon") is None:
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [d["lon"], d["lat"]]},
            "properties": {
                "id": d["id"], "label": d["label"], "confidence": round(d["conf"], 3),
                "status": d["status"], "source_image": d.get("image", ""),
                "position_quality": d.get("position_quality"),
                "reviewed_by": d.get("reviewed_by"), "reviewed_utc": d.get("reviewed_utc"),
            },
        })
    return {
        "type": "FeatureCollection",
        "features": feats,
        "properties": {"generator": "Survey Signal v0.1.0", "disclaimer": DISCLAIMER,
                       "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat()},
    }


def to_kml(detections: list[dict], statuses=("confirmed",)) -> str:
    placemarks = []
    for d in detections:
        if d["status"] not in statuses or d.get("lon") is None:
            continue
        placemarks.append(
            f"<Placemark><name>{escape(d['label'])} ({d['conf']:.2f})</name>"
            f"<description>id={escape(d['id'])} status={d['status']} "
            f"position={escape(d.get('position_quality') or 'unknown')} "
            f"image={escape(d.get('image', ''))}</description>"
            f"<Point><coordinates>{d['lon']},{d['lat']},0</coordinates></Point></Placemark>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"<name>Survey Signal hazard candidates</name><description>{escape(DISCLAIMER)}</description>"
        + "".join(placemarks) + "</Document></kml>"
    )


_REPORT = Template("""<!doctype html><html><head><meta charset="utf-8">
<title>Survey Signal survey-assist report</title>
<style>body{font-family:system-ui;margin:2rem;max-width:52rem}
.warn{background:#fff3cd;border:2px solid #d9a400;padding:1rem;border-radius:8px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}
</style></head><body>
<h1>Survey Signal survey-assist report</h1>
<p class="warn"><strong>⚠ {{ disclaimer }}</strong></p>
<table>
<tr><th>Generated (UTC)</th><td>{{ generated }}</td></tr>
<tr><th>Analyst</th><td>{{ analyst }}</td></tr>
<tr><th>Model</th><td>{{ model }}</td></tr>
<tr><th>Images processed</th><td>{{ n_images }}</td></tr>
<tr><th>Candidates flagged</th><td>{{ n_total }}</td></tr>
<tr><th>Confirmed / Rejected / Unsure / Pending</th><td>{{ n_confirmed }} / {{ n_rejected }} / {{ n_unsure }} / {{ n_pending }}</td></tr>
</table>
<h2>Confirmed &amp; unsure candidates</h2>
<table><tr><th>ID</th><th>Label</th><th>Conf</th><th>Status</th><th>Lat</th><th>Lon</th>
<th>Position</th><th>Reviewed by</th><th>Reviewed (UTC)</th><th>Image</th></tr>
{% for d in rows %}<tr><td>{{ d.id }}</td><td>{{ d.label }}</td><td>{{ "%.2f"|format(d.conf) }}</td>
<td>{{ d.status }}</td><td>{{ "%.6f"|format(d.lat) if d.lat is not none else "—" }}</td>
<td>{{ "%.6f"|format(d.lon) if d.lon is not none else "—" }}</td>
<td>{{ d.position_quality or "—" }}</td><td>{{ d.reviewed_by or "—" }}</td>
<td>{{ d.reviewed_utc or "—" }}</td><td>{{ d.image }}</td></tr>{% endfor %}
</table>
<h2>Imagery and georeferencing</h2>
<p>Position quality: <em>georeferenced</em> = GeoTIFF transform; <em>approximate</em> = camera
footprint from measured flight data (metres-level); <em>unverified</em> = one or more footprint
inputs were assumed, listed below. Verify unverified positions against the source image.</p>
<table><tr><th>Image</th><th>SHA-256</th><th>Position quality</th><th>Georeferencing notes</th></tr>
{% for i in images %}<tr><td>{{ i.file }}</td><td><code>{{ i.sha256[:16] }}…</code></td>
<td>{{ i.geo.quality if i.geo else "no position" }}</td>
<td>{% if i.geo %}{% for w in i.geo.warnings %}⚠ {{ w }}<br>{% endfor %}
{% if i.geo.method == "exif_footprint" %}height {{ i.geo.altitude_agl_m }} m ({{ i.geo.altitude_source }});
heading {{ i.geo.yaw_deg }}° ({{ i.geo.yaw_source }}); scale from {{ i.geo.gsd_source }}{% else %}GeoTIFF affine transform{% endif %}
{% else %}No GPS or CRS: detections from this image are not exported.{% endif %}</td></tr>{% endfor %}
</table></body></html>""", autoescape=True)


def to_report_html(detections: list[dict], model_name: str, n_images: int,
                   analyst: str = "unspecified", images: list[dict] | None = None) -> str:
    def by(status: str) -> list[dict]:
        return [d for d in detections if d["status"] == status]

    rows = [d for d in detections if d["status"] in ("confirmed", "unsure")]
    return _REPORT.render(
        disclaimer=DISCLAIMER,
        generated=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        analyst=analyst, model=model_name, n_images=n_images, n_total=len(detections),
        n_confirmed=len(by("confirmed")), n_rejected=len(by("rejected")),
        n_unsure=len(by("unsure")), n_pending=len(by("pending")), rows=rows,
        images=images or [],
    )


def dumps(obj) -> str:
    return json.dumps(obj, indent=2)

"""Lambda handlers for Stockholm Departure Board."""

import json
import os
import time
import urllib.request

SL_BASE = "https://transport.integration.sl.se/v1"
GTFS_RT_URL = "https://opendata.samtrafiken.se/gtfs-rt/sl/VehiclePositions.pb"

_sites_cache = None
_sites_cache_time = 0
CACHE_TTL = 3600  # 1 hour


def _respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def _fetch_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _fetch_bytes(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/x-protobuf'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def _get_sites():
    global _sites_cache, _sites_cache_time
    now = time.time()
    if _sites_cache is None or now - _sites_cache_time > CACHE_TTL:
        _sites_cache = _fetch_json(f"{SL_BASE}/sites?expand=true")
        _sites_cache_time = now
    return _sites_cache


def search_sites(event, context):
    params = event.get("queryStringParameters") or {}
    query = params.get("q", "")
    if len(query) < 2:
        return _respond(400, {"error": 'Query parameter "q" must be at least 2 characters'})

    try:
        data = _get_sites()
        filtered = [
            {"id": s["id"], "name": s["name"]}
            for s in data
            if query.lower() in s.get("name", "").lower()
        ][:15]
        return _respond(200, filtered)
    except Exception as e:
        print(f"searchSites error: {e}")
        return _respond(502, {"error": "Failed to fetch sites from SL API"})


def get_departures(event, context):
    path_params = event.get("pathParameters") or {}
    site_id = path_params.get("siteId")
    if not site_id:
        return _respond(400, {"error": "Missing siteId"})

    params = event.get("queryStringParameters") or {}
    dest_filter = params.get("destination", "").lower()

    try:
        data = _fetch_json(f"{SL_BASE}/sites/{site_id}/departures")
        departures = []
        for d in data.get("departures") or []:
            if dest_filter and dest_filter not in d.get("destination", "").lower():
                continue
            departures.append({
                "line": d.get("line", {}).get("designation", ""),
                "destination": d.get("destination", ""),
                "direction": d.get("direction"),
                "displayTime": d.get("display", ""),
                "expected": d.get("expected") or d.get("scheduled", ""),
                "transportMode": d.get("line", {}).get("transport_mode", ""),
                "deviations": [dev.get("message", "") for dev in d.get("deviations", [])],
                "journeyId": str(d.get("journey", {}).get("id", "")),
            })
            if len(departures) >= 30:
                break
        return _respond(200, {"siteId": site_id, "departures": departures})
    except Exception as e:
        print(f"getDepartures error: {e}")
        return _respond(502, {"error": "Failed to fetch departures from SL API"})


def get_vehicle_position(event, context):
    params = event.get("queryStringParameters") or {}
    journey_id = params.get("journeyId", "").strip()
    if not journey_id:
        return _respond(400, {"error": "Missing journeyId"})

    api_key = os.environ.get("TRAFIKLAB_API_KEY", "")
    if not api_key:
        return _respond(500, {"error": "TRAFIKLAB_API_KEY not configured"})

    try:
        from google.transit import gtfs_realtime_pb2

        raw = _fetch_bytes(f"{GTFS_RT_URL}?key={api_key}")
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(raw)

        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue
            vp = entity.vehicle
            if vp.trip.trip_id == journey_id:
                pos = vp.position
                return _respond(200, {
                    "found": True,
                    "lat": pos.latitude,
                    "lon": pos.longitude,
                    "bearing": pos.bearing if pos.bearing else None,
                    "speed": pos.speed if pos.speed else None,
                    "timestamp": vp.timestamp,
                })

        return _respond(200, {"found": False})
    except Exception as e:
        print(f"getVehiclePosition error: {e}")
        return _respond(502, {"error": "Failed to fetch vehicle position"})

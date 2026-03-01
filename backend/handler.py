"""Lambda handlers for Stockholm Departure Board."""

import json
import urllib.request

SL_BASE = "https://transport.integration.sl.se/v1"


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


def search_sites(event, context):
    params = event.get("queryStringParameters") or {}
    query = params.get("q", "")
    if len(query) < 2:
        return _respond(400, {"error": 'Query parameter "q" must be at least 2 characters'})

    try:
        data = _fetch_json(f"{SL_BASE}/sites?expand=true")
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
            })
            if len(departures) >= 30:
                break
        return _respond(200, {"siteId": site_id, "departures": departures})
    except Exception as e:
        print(f"getDepartures error: {e}")
        return _respond(502, {"error": "Failed to fetch departures from SL API"})

#!/usr/bin/env python3
"""
Kolarängen Busstavla - MVP
Visar realtidsavgångar från Kolarängen med SL Transport API.

Användning:
    python3 departures.py
    python3 departures.py --station "T-Centralen"
    python3 departures.py --loop
"""

import json
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

SL_API_BASE = "https://transport.integration.sl.se/v1"


def _ssl_context():
    """Skapa SSL-kontext, med certifi som fallback för macOS."""
    try:
        ctx = ssl.create_default_context()
        # Testa att kontexten fungerar genom att ladda standardcertifikat
        if not ctx.get_ca_certs():
            raise ssl.SSLError("no certs loaded")
        return ctx
    except Exception:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    # Sista utväg: använd systemets certifikat utan extra validering
    ctx = ssl.create_default_context()
    return ctx


_ctx = _ssl_context()


def fetch_json(url):
    """Hämta JSON från en URL."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10, context=_ctx) as resp:
        return json.loads(resp.read())


def find_site(name):
    """Sök efter en hållplats med namn."""
    sites = fetch_json(f"{SL_API_BASE}/sites")
    matches = [
        s for s in sites
        if name.lower() in s.get("name", "").lower()
    ]
    return matches


def get_departures(site_id):
    """Hämta avgångar för en hållplats."""
    data = fetch_json(f"{SL_API_BASE}/sites/{site_id}/departures")
    return data.get("departures", [])


def format_time(dep):
    """Formatera visningstid för en avgång."""
    return dep.get("display", "")


def transport_icon(mode):
    """Returnera ikon för transporttyp."""
    icons = {
        "BUS": "Buss",
        "METRO": "T-bana",
        "TRAIN": "Tåg",
        "TRAM": "Spårv",
        "SHIP": "Båt",
    }
    return icons.get(mode, mode or "?")


def print_departures(site_name, departures):
    """Skriv ut avgångar i en snygg tabell."""
    print()
    print(f"  Avgångar från {site_name}")
    print(f"  Uppdaterad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not departures:
        print("  Inga avgångar hittades.")
        return

    # Header
    print(f"  {'Typ':<7} {'Linje':<7} {'Destination':<30} {'Avgång'}")
    print(f"  {'-'*7} {'-'*7} {'-'*30} {'-'*10}")

    for dep in departures[:20]:
        mode = transport_icon(dep.get("line", {}).get("transport_mode", ""))
        line = dep.get("line", {}).get("designation", "?")
        destination = dep.get("destination", "Okänd")
        display = format_time(dep)

        print(f"  {mode:<7} {line:<7} {destination:<30} {display}")

        # Visa störningar om det finns
        deviations = dep.get("deviations", [])
        for dev in deviations:
            msg = dev.get("message", "")
            if msg:
                print(f"          ⚠ {msg}")

    print()


def main():
    station_name = "Kolarängen"

    # Hantera kommandoradsargument
    loop_mode = "--loop" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "--station" and i + 1 < len(sys.argv):
            station_name = sys.argv[i + 1]

    # Hitta hållplats
    print(f"Söker efter hållplats: {station_name}...")
    try:
        sites = find_site(station_name)
    except urllib.error.URLError as e:
        print(f"Kunde inte ansluta till SL API: {e}")
        sys.exit(1)

    if not sites:
        print(f"Hittade ingen hållplats med namn '{station_name}'")
        sys.exit(1)

    site = sites[0]
    site_id = site["id"]
    site_name = site["name"]
    print(f"Hittade: {site_name} (ID: {site_id})")

    if len(sites) > 1:
        print(f"  ({len(sites)} träffar totalt, använder första)")

    while True:
        try:
            departures = get_departures(site_id)
            print_departures(site_name, departures)
        except urllib.error.URLError as e:
            print(f"Fel vid hämtning av avgångar: {e}")

        if not loop_mode:
            break

        print("Uppdaterar om 30 sekunder... (Ctrl+C för att avsluta)")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\nAvslutar.")
            break


if __name__ == "__main__":
    main()

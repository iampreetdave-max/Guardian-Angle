"""Ahmedabad geography constants for the City Map and complaint tagging.

Approximate locality centroids (WGS84). Good enough to place a complaint or a
camera on the city map; not survey-grade. Names follow common local usage so
they read naturally in the complaint form dropdown.
"""
from __future__ import annotations

AHMEDABAD_CENTER: tuple[float, float] = (23.0225, 72.5714)

AREAS: dict[str, tuple[float, float]] = {
    "Navrangpura": (23.0366, 72.5611),
    "Ellisbridge": (23.0258, 72.5680),
    "Paldi": (23.0117, 72.5624),
    "Vasna": (23.0030, 72.5530),
    "Vejalpur": (23.0019, 72.5226),
    "Satellite": (23.0301, 72.5108),
    "Vastrapur": (23.0395, 72.5293),
    "Bodakdev": (23.0479, 72.5085),
    "Thaltej": (23.0509, 72.5060),
    "Bopal": (23.0333, 72.4642),
    "SG Highway": (23.0443, 72.5023),
    "Gota": (23.1007, 72.5316),
    "Ghatlodia": (23.0710, 72.5421),
    "Memnagar": (23.0541, 72.5380),
    "Ranip": (23.0810, 72.5662),
    "Chandkheda": (23.1126, 72.5814),
    "Sabarmati": (23.0823, 72.5806),
    "Shahibaug": (23.0556, 72.5946),
    "Asarwa": (23.0455, 72.6065),
    "Bapunagar": (23.0345, 72.6358),
    "Naroda": (23.0708, 72.6593),
    "Nikol": (23.0490, 72.6646),
    "Odhav": (23.0211, 72.6708),
    "Gomtipur": (23.0153, 72.6166),
    "Maninagar": (22.9962, 72.6027),
    "Kankaria": (23.0063, 72.6024),
    "Isanpur": (22.9750, 72.6111),
    "Vatva": (22.9586, 72.6332),
    "Behrampura": (22.9939, 72.5824),
    "Jamalpur": (23.0118, 72.5862),
}


def area_names() -> list[str]:
    return list(AREAS.keys())


def area_centroid(name: str | None) -> tuple[float, float] | None:
    if not name:
        return None
    return AREAS.get(name)

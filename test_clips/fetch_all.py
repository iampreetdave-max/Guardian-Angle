"""Re-fetch the CC-licensed anomaly test clips documented in MANIFEST.md from
Wikimedia Commons into their category folders. Idempotent: skips files that
already exist and verify as playable. Run from the repo root or test_clips/:

    python test_clips/fetch_all.py            # all anomaly categories + normal
    python test_clips/fetch_all.py fire smoke # only the named categories
"""
from __future__ import annotations

import os
import sys

import cv2
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "VisionScan-test-clip-builder/1.0 (agilitytechai@gmail.com)"}

# category -> list of (Commons File: title, local filename)
CLIPS: dict[str, list[tuple[str, str]]] = {
    "fire": [
        ("File:2010_Shanghai_fire_video.ogv", "fire_highrise_shanghai_01.ogv"),
        ("File:Long_Bar_Fire_-_2020-09-04.ogv", "fire_wildfire_longbar_02.ogv"),
    ],
    "smoke": [
        ("File:Smoke_Plume_over_the_Howe_Ridge_Fire_August_12th_2018_(43360971394).webm",
         "smoke_wildfire_howeridge_01.webm"),
        ("File:Chimney_smoke_video_dec_09.ogv", "smoke_chimney_groundlevel_02.ogv"),
    ],
    "accident": [
        ("File:Fatal_Hit_and_Run_Traffic_Collision_NR24134dm.webm",
         "accident_collision_lapd_01.webm"),
        ("File:Felony_Hit_and_Run_Traffic_Collision_1-22-2024_NR24209rc.webm",
         "accident_collision_lapd_02.webm"),
    ],
    "weapon": [
        ("File:Knife_Skills-_Slicing_Steak_For_Stir_Fry.webm", "weapon_knife_slicing_01.webm"),
        ("File:Shooting_Range_Nokia_E71.webm", "weapon_pistol_shootingrange_02.webm"),
    ],
    "violence": [
        ("File:Krav_Maga_demonstration.ogv", "violence_kravmaga_demo_01.ogv"),
        ("File:Taekwondo-wedstrijd_tussen_Nederland_en_Zuid-Korea_Weeknummer,_79-46_-_Open_Beelden_-_56237.ogv",
         "violence_taekwondo_match_02.ogv"),
    ],
    "normal": [
        ("File:Calle_preciados.ogv", "normal_pedestrian_street_madrid_01.ogv"),
        ("File:Tirana_traffic_lights.webm", "normal_traffic_intersection_tirana_02.webm"),
    ],
}


def direct_url(title: str) -> str:
    r = requests.get(API, params={
        "action": "query", "titles": title, "prop": "imageinfo",
        "iiprop": "url", "format": "json",
    }, headers=HEADERS, timeout=60)
    page = next(iter(r.json()["query"]["pages"].values()))
    return page["imageinfo"][0]["url"]


def playable(path: str) -> tuple[bool, int, int, float | None]:
    cap = cv2.VideoCapture(path)
    ok = cap.isOpened()
    fps = cap.get(cv2.CAP_PROP_FPS) if ok else 0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) if ok else 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if ok else 0
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if ok else 0
    cap.release()
    return ok, w, h, (n / fps if fps and n else None)


def main() -> None:
    cats = sys.argv[1:] or list(CLIPS)
    total_ok = total_fail = 0
    for cat in cats:
        items = CLIPS.get(cat)
        if not items:
            print(f"[skip] unknown category {cat!r}")
            continue
        folder = os.path.join(HERE, cat)
        os.makedirs(folder, exist_ok=True)
        for title, fname in items:
            dest = os.path.join(folder, fname)
            if os.path.exists(dest) and playable(dest)[0]:
                print(f"[have] {cat}/{fname}")
                total_ok += 1
                continue
            try:
                url = direct_url(title)
                with requests.get(url, headers=HEADERS, stream=True, timeout=300) as resp:
                    resp.raise_for_status()
                    with open(dest, "wb") as fh:
                        for chunk in resp.iter_content(1 << 16):
                            fh.write(chunk)
                ok, w, h, dur = playable(dest)
                mb = os.path.getsize(dest) / 1e6
                if ok:
                    total_ok += 1
                    print(f"[ok]   {cat}/{fname}  {w}x{h}  {dur:.1f}s  {mb:.1f}MB" if dur
                          else f"[ok]   {cat}/{fname}  {w}x{h}  {mb:.1f}MB")
                else:
                    total_fail += 1
                    print(f"[BAD]  {cat}/{fname} downloaded but cv2 cannot open it")
            except Exception as exc:  # noqa: BLE001
                total_fail += 1
                print(f"[FAIL] {cat}/{fname}: {exc}")
    print(f"\n{total_ok} clip(s) ready, {total_fail} failed.")


if __name__ == "__main__":
    main()

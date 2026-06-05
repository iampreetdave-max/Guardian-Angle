# VisionScan Test-Clip Library — MANIFEST

Test clips for CCTV anomaly detection (CLIP zero-shot + YOLO) and face/object search.

- **Source:** All clips from Wikimedia Commons (https://commons.wikimedia.org), CC-licensed or Public Domain — legally redistributable with attribution where noted.
- **Containers:** `.webm` (VP8/VP9) and `.ogv` (Theora). Verified playable via `cv2.VideoCapture(path).isOpened() == True` using the project venv (opencv-python 4.11).
- **No ffmpeg** was available in the environment, so clips were not transcoded or trimmed; only naturally short source files were selected.
- **Total: 16 clips, ~135 MB** (budget was < 500 MB).
- Clips are git-ignored (`test_clips/.gitignore` = `*`). Do not commit binaries.

Attribution note: CC BY / CC BY-SA files require crediting the original author and license if redistributed. Click any source URL's file page on Commons for the exact author/attribution string.

---

## fire (2 files, 11.9 MB)

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| fire_highrise_shanghai_01.ogv | https://commons.wikimedia.org/wiki/File:2010_Shanghai_fire_video.ogv | CC BY 2.0 | 21.3s | 640x480 |
| fire_wildfire_longbar_02.ogv | https://commons.wikimedia.org/wiki/File:Long_Bar_Fire_-_2020-09-04.ogv | Public domain | 11.4s | 1280x720 |

## smoke (2 files, 4.5 MB)

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| smoke_wildfire_howeridge_01.webm | https://commons.wikimedia.org/wiki/File:Smoke_Plume_over_the_Howe_Ridge_Fire_August_12th_2018_(43360971394).webm | Public domain | 30.4s | 1920x1080 |
| smoke_chimney_groundlevel_02.ogv | https://commons.wikimedia.org/wiki/File:Chimney_smoke_video_dec_09.ogv | CC BY-SA 3.0 | 10.6s | 640x480 |

## accident (2 files, 5.9 MB)

Official US police-released traffic-collision footage (CCTV/witness angle) — ideal for CCTV crash detection. Public domain (work of US government / LAPD release).

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| accident_collision_lapd_01.webm | https://commons.wikimedia.org/wiki/File:Fatal_Hit_and_Run_Traffic_Collision_NR24134dm.webm | Public domain | 7.7s | 2560x1440 |
| accident_collision_lapd_02.webm | https://commons.wikimedia.org/wiki/File:Felony_Hit_and_Run_Traffic_Collision_1-22-2024_NR24209rc.webm | Public domain | 28.0s | 1920x1080 |

## weapon (2 files, 15.0 MB)

Benign, legal demonstrations (person holding a knife; pistol at a shooting range).

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| weapon_knife_slicing_01.webm | https://commons.wikimedia.org/wiki/File:Knife_Skills-_Slicing_Steak_For_Stir_Fry.webm | CC BY 3.0 | 59.5s | 854x480 |
| weapon_pistol_shootingrange_02.webm | https://commons.wikimedia.org/wiki/File:Shooting_Range_Nokia_E71.webm | CC BY 2.0 | 81.3s | 480x360 |

## violence (2 files, 37.2 MB)

Martial-arts demonstrations / sparring — benign training footage.

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| violence_kravmaga_demo_01.ogv | https://commons.wikimedia.org/wiki/File:Krav_Maga_demonstration.ogv | CC BY-SA 4.0 | 47.3s | 1920x1080 |
| violence_taekwondo_match_02.ogv | https://commons.wikimedia.org/wiki/File:Taekwondo-wedstrijd_tussen_Nederland_en_Zuid-Korea_Weeknummer,_79-46_-_Open_Beelden_-_56237.ogv | CC BY-SA 3.0 NL | 116.4s | 352x288 |

## normal (3 files, 23.2 MB) — calibration control set

Ordinary street / pedestrian / traffic footage.

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| normal_pedestrian_street_madrid_01.ogv | https://commons.wikimedia.org/wiki/File:Calle_preciados.ogv | CC BY-SA 3.0 | 19.0s | 1280x720 |
| normal_traffic_intersection_tirana_02.webm | https://commons.wikimedia.org/wiki/File:Tirana_traffic_lights.webm | CC BY 4.0 | 12.8s | 1816x1022 |
| normal_pedestrians_walking_03.ogv | https://commons.wikimedia.org/wiki/File:Hesitant-avoidance-while-walking-an-error-of-social-behavior-generated-by-mutual-interaction-Video1.ogv | CC BY 4.0 | 14.4s | 320x240 |

## faces (3 files, 37.5 MB)

Single-person talking-head clips (WIKITONGUES language recordings) — clear, well-lit frontal faces, good for face detection/search.

| Filename | Source URL | License | Duration | Resolution |
|---|---|---|---|---|
| faces_talkinghead_mirela_01.webm | https://commons.wikimedia.org/wiki/File:WIKITONGUES-_Mirela_speaking_Bosnian.webm | CC BY 3.0 | 112.8s | 640x480 |
| faces_talkinghead_rizki_02.webm | https://commons.wikimedia.org/wiki/File:WIKITONGUES-_Rizki_speaking_Malay.webm | CC BY-SA 4.0 | 58.4s | 1080x606 |
| faces_talkinghead_orsolya_03.webm | https://commons.wikimedia.org/wiki/File:WIKITONGUES-_Orsolya_speaking_Hungarian.webm | CC BY 3.0 | 90.2s | 1920x1080 |

---

## Notes / gaps

- Every category has 2-3 verified clips; none came up empty. `normal` and `faces` have 3 each as requested.
- `accident` clips are short (LAPD release footage); both are genuine vehicle collisions captured on camera — well suited to CCTV crash detection.
- `weapon` and `violence` use benign demonstrations only (knife cooking demo, shooting-range, Krav Maga / Taekwondo) — no graphic/illegal content.
- A couple of clips exceed the 90s ideal (knife 59s OK; pistol 81s; faces Mirela 112s; taekwondo 116s) but all stay modest in size due to good compression. No clip exceeds ~27 MB.
- Containers are `.webm`/`.ogv` rather than `.mp4` because no ffmpeg was present to transcode; opencv reads them fine (all verified `isOpened()==True`). If `.mp4` is later required, install ffmpeg and run `ffmpeg -i in.webm -c:v libx264 out.mp4`.
- Helper script used to fetch + probe: `test_clips/_fetch_commons.py` (kept for reproducibility; ignored by git).

# Real2Sim G1 bemutató - PPT vázlat

Ez a fájl PowerPoint készítéshez készült. A cél: 8-10 perces, érthető versenybemutató, ahol először a stabil kétkaros megoldás látszik, utána opcionálisan a teljes test kísérleti bővítés.

## 1. dia - Cím

**Real2Sim emberi mozgás utánzás Unitree G1 humanoiddal**

Kulcsmondat:
- Kamera látja az embert.
- MediaPipe kinyeri a testpontokat.
- Python retargeting átszámolja robotízületekre.
- MuJoCo-ban a Unitree G1 modell követi a mozgást.
- OpenClaw-kompatibilis parancsokkal indítható.

## 2. dia - Feladat és MVP cél

Versenyfeladat:
- Human upper-body motion camera inputból.
- Legalább két kar utánzása.
- Unitree G1 robotmodell.
- MuJoCo szimulátor.
- OpenClaw user-facing wrapper.

MVP döntés:
- Nem teljes humanoid dinamikai kontrollert építettünk.
- A cél egy robusztus, demonstrálható real2sim pipeline.
- A stabil beadási verzió a kétkaros imitáció.
- A teljes test verzió extra demonstráció: törzs, guggolás, láb, root mozgás.

## 3. dia - Architektúra

```text
Webcam / két kamera / videó
        |
        v
OpenCV frame capture
        |
        v
MediaPipe Pose landmarks
        |
        v
váll, könyök, csukló, csípő, térd, boka pontok
        |
        v
ArmRetargeter: emberi vektorok -> G1 target szögek
        |
        v
MujocoG1Controller: target qpos beírás
        |
        v
Unitree G1 MuJoCo viewer
        |
        v
OpenClaw wrapper / START_DEMO launcher
```

## 4. dia - Fájlstruktúra

Fontos fájlok:
- `src/camera_pose.py`: OpenCV + MediaPipe pose extraction.
- `src/stereo_pose.py`: két kamera 3D trianguláció.
- `src/retarget.py`: emberi pose -> robot ízületi targetek.
- `src/mujoco_g1.py`: Unitree G1 MuJoCo vezérlés.
- `src/openclaw_real2sim_tool.py`: OpenClaw-kompatibilis CLI wrapper.
- `configs/g1_arm_mapping_STABLE_ARMS.yaml`: stabil beadási kétkaros config.
- `configs/g1_arm_mapping.yaml`: teljes test kísérleti config.
- `START_ARMS_ONLY.bat`: stabil kétkaros demó.
- `START_FULL_BODY.bat`: teljes test demó.
- `START_DEMO.bat`: választómenüs indító.

## 5. dia - Kamera és kalibráció

Alap kamera setup:
- Laptop kamera: `0`
- USB kamera: `1`
- USB kamera szoftveres forgatás: `right_rotation: cw`
- Kalibráció: ChArUco tábla képpárokból

Indítás:

```powershell
.\CLEAR_CALIBRATION_IMAGES.bat
python scripts\capture_stereo_charuco.py
.\FILTER_WEAK_CALIBRATION_IMAGES.bat
python scripts\calibrate_stereo_charuco.py --input-dir data/stereo_charuco --output configs\stereo_calibration.yaml
```

A `CLEAR_CALIBRATION_IMAGES.bat` kitörli a régi `left_*.png` és `right_*.png` kalibrációs képeket, hogy az új és régi kalibrációs párok ne keveredjenek. Biztonságos ellenőrzés:

```powershell
python scripts\clear_stereo_charuco.py --dry-run
```

A `FILTER_WEAK_CALIBRATION_IMAGES.bat` újraszámolja a ChArUco sarkokat, és kitörli azokat a képpárokat, ahol bal vagy jobb oldalon 12-nél kevesebb sarok látszik.

A `capture_stereo_charuco.py` most a fő configból veszi a kamera indexeket és forgatást:

```yaml
stereo:
  left_camera: 0
  right_camera: 1
  backend: "dshow"
  left_rotation: "none"
  right_rotation: "cw"
```

## 6. dia - Pose detection

MediaPipe Pose landmarkok:
- bal/jobb váll
- bal/jobb könyök
- bal/jobb csukló
- bal/jobb csípő
- teljes test módban térd és boka

Lényeges kódrészlet: [src/camera_pose.py]

```python
points[name] = np.array(
    [float(landmark.x), float(landmark.y), float(landmark.z)],
    dtype=np.float64,
)
```

Stabilitási megoldás:
- Upper-body pontokra szigorúbb confidence.
- Lower-body pontokra lazább confidence.
- Ha térd/boka eltűnik, nem áll le az egész pipeline.

## 7. dia - Stereo 3D logika

Két kamera esetén:
- Mindkét képen MediaPipe landmark detection.
- Pixelkoordináták torzítás-korrekciója.
- OpenCV `triangulatePoints`.
- 3D pontok a bal kamera koordináta-rendszerében.

Lényeges kódrészlet: [src/stereo_pose.py]

```python
homogeneous = cv2.triangulatePoints(
    cal.left_projection,
    cal.right_projection,
    left_undistorted,
    right_undistorted,
)
point = homogeneous[:3, 0] / homogeneous[3, 0]
```

Miért kell stereo?
- Egyetlen frontális kamerából a kéz mélysége bizonytalan.
- Két kamera segít megkülönböztetni, hogy a kéz előre vagy oldalra mozdul.

## 8. dia - Retargeting, karok

Kar retargeting:
- Váll-könyök vektor: felkar.
- Könyök-csukló vektor: alkar.
- Törzs lokális koordinátarendszer: up, right, forward.
- Felkar vetítése ebbe a frame-be.
- Ebből shoulder pitch és shoulder roll.
- Könyökhajlítás: felkar és alkar bezárt szöge.

Lényeges kódrészlet: [src/retarget.py]

```python
upper_arm = elbow - shoulder
forearm = wrist - elbow

shoulder_pitch = atan2(forward_component, down_component)
shoulder_roll = atan2(side_component, down_component)

elbow_angle = _angle_between(-upper_arm, forearm)
elbow_flexion = clamp(pi - elbow_angle, 0.0, pi)
```

## 9. dia - Smoothing és limitek

Miért kell smoothing?
- MediaPipe landmarkok zajosak.
- Kamera occlusion miatt ugrálhatnak a pontok.
- Robotmozgás remegne smoothing nélkül.

Megoldás:

```python
smoothed[name] = alpha * value + (1.0 - alpha) * previous
```

Joint limit clamp:

```python
targets[name] = clamp(value, low, high)
```

Eredmény:
- Stabilabb kar.
- A robot nem megy irreális pózokba.

## 10. dia - MuJoCo és Unitree G1

Robotmodell:
- Unitree G1 XML a Unitree MuJoCo repositoryból.
- MuJoCo Python csomag tölti be.
- MVP módban direkt `qpos` célértékeket írunk.

Lényeges kódrészlet: [src/mujoco_g1.py]

```python
qpos_index = self.joint_name_to_qpos_index[mujoco_joint_name]
self.data.qpos[qpos_index] = float(angle)
self.mujoco.mj_forward(self.model, self.data)
```

Miért direkt qpos?
- A verseny MVP-hez vizuális imitáció kell.
- Teljes dinamikai humanoid stabilizálás sokkal nagyobb feladat.
- A direkt qpos stabil és demonstrálható.

## 11. dia - OpenClaw wrapper

OpenClaw-kompatibilis CLI:

```powershell
python src\openclaw_real2sim_tool.py status
python src\openclaw_real2sim_tool.py run-demo --camera 0
python src\openclaw_real2sim_tool.py record-demo --output media\demo_output.mp4
```

Beadási indítók:

```powershell
.\START_DEMO.bat
```

Menü:
- `1`: stabil kétkaros verzió
- `2`: teljes test kísérleti verzió

## 12. dia - Stabil kétkaros demó

Indító:

```powershell
.\START_ARMS_ONLY.bat
```

Mit mutatunk:
- Bal kar követi a bal kart.
- Jobb kar követi a jobb kart.
- Könyökhajlítás működik.
- T-pose / karok széttárása / kar leengedése.
- Pose detection kiesésnél robot tartja az utolsó stabil pózt.

Miért ez a beadási főverzió?
- Ez felel meg biztosan a minimum követelménynek.
- Ez volt a legtöbbet tesztelt és legstabilabb pipeline.

## 13. dia - Teljes test kísérleti demó

Indító:

```powershell
.\START_FULL_BODY.bat
```

Extra funkciók:
- Derék előrehajlás.
- Guggolás medence-süllyedés alapján.
- Csípő és térd kísérleti retargeting.
- Root motion kísérlet a medence elmozdulásából.

Fontos: ez kísérleti, mert a láb landmarkok sokkal könnyebben eltűnnek kameraképből, mint a karok.

## 14. dia - Squat assist logika

Probléma:
- Térd és boka landmarkok gyakran eltűnnek.
- Két webcam szűk látószöge miatt full-body tracking instabil.

Megoldás:
- Ha a medence lejjebb kerül a kalibrált álló pózhoz képest, a robot kap extra térd- és csípőhajlítást.
- Ez akkor is működik valamennyire, ha a térd/boka pontok bizonytalanok.

Lényeges kódrészlet: [src/retarget.py]

```python
pelvis_drop = metrics["pelvis_y"] - self.neutral_metrics["pelvis_y"]
amount = clamp((pelvis_drop - min_drop) / (full_drop - min_drop), 0.0, 1.0)

adjusted[knee_name] = clamp(adjusted.get(knee_name, 0.0) + knee_add, low, high)
adjusted[hip_name] = clamp(adjusted.get(hip_name, 0.0) + hip_pitch_add, low, high)
```

## 15. dia - Demó forgatókönyv

1. Projekt mappa megnyitása:

```powershell
cd C:\Users\dallo\Desktop\SZTAKI_Robot\real2sim-g1
```

2. Menüs indító:

```powershell
.\START_DEMO.bat
```

3. VS Code nem szükséges. Kalibrációhoz használható a menüs indító:

```powershell
.\CALIBRATION_MENU.bat
```

Menü:
- `1`: régi kalibrációs képek törlése
- `2`: új ChArUco képpárok felvétele
- `3`: 12 alatti gyenge képpárok törlése
- `4`: stereo kalibráció kiszámítása

4. Új stereo kalibráció előtt régi képek törlése:

```powershell
.\CLEAR_CALIBRATION_IMAGES.bat
```

5. Először `1`: stabil karos beadási demó.

6. Mozdulatok:
- karok leengedve
- T-pose
- könyök hajlítás
- jobb/bal kar külön mozgás

7. Utána opcionálisan `2`: teljes test kísérleti demó.

8. Mozdulatok:
- előrehajlás
- guggolás
- enyhe csípő/törzs mozgás

## 16. dia - Korlátok

Őszinte korlátok:
- Nem real robot control, csak MuJoCo vizualizáció.
- Nem teljes dinamikai humanoid controller.
- MediaPipe zajos lehet.
- Kamera occlusion: térd/boka könnyen eltűnik.
- A G1 és az ember kinematikája eltér.
- Stereo kalibráció érzékeny a kamerák pozíciójára.
- Full-body tracking kísérleti, a stabil beadási rész a két kar.

## 17. dia - Eredmény

Teljesített pontok:
- Python MVP projekt.
- Webcam/videó input.
- MediaPipe pose detection.
- Kétkaros retargeting.
- Unitree G1 MuJoCo modell.
- OpenClaw wrapper.
- Stereo bővítés.
- Full-body kísérleti bővítés.
- Dokumentáció és CC license notice.
- Külön stabil és kísérleti indítók.

## 18. dia - Zárómondat

A projekt célja egy demonstrálható real2sim rendszer volt, nem egy teljes humanoid balansz-kontroller. A stabil verzió megbízhatóan teljesíti a verseny minimumát: két emberi kar mozgásának utánzása Unitree G1 modellen MuJoCo-ban. A teljes test verzió megmutatja a továbbfejlesztési irányt: több kamera, jobb kalibráció, robusztusabb 3D testkövetés és későbbi PD/actuator kontroll.

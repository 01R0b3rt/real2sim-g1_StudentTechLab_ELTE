# Real2Sim G1 - StudentTechLab ELTE

```text
===============================================================================
 REAL2SIM G1                                             SZTAKI / TTAH 2026
===============================================================================

                                 ####
                             ##########
                         ###############          #######
                     ###############          #############
                 ###############          #####################
                ##########          #############     #########
                #######        #############             ######
                #######      ###########                 ######
                #######      #######          ######     ######
                #######                    #########     ######
                #######               #############      ######
                #########       #############          ########
                ########################          #############
                    ################          #############
                         #######          #############
                            #          ###########
                                      #######

                             STUDENT TECH LAB ELTE

                   Camera -> MediaPipe -> MuJoCo Unitree G1
===============================================================================
```

## Project Purpose / Projekt célja

This project is a practical MVP for a real-to-simulation competition pipeline. A camera observes human motion, MediaPipe extracts body landmarks, and a Unitree G1 humanoid model in MuJoCo imitates the detected movement. The stable submission mode focuses on robust two-arm imitation; the repository also includes an experimental stereo full-body mode for squatting, leaning, and basic leg motion.

Ez a projekt egy gyakorlati MVP egy real-to-simulation versenyfeladathoz. A rendszer kameraképből felismeri az emberi testpontokat, a karok és a test mozgását egyszerű retargeting logikával robot ízületi célokra képezi le, majd a Unitree G1 humanoid modellt MuJoCo szimulátorban mozgatja. A beadáshoz használható stabil verzió a kétkaros utánzást helyezi előtérbe; emellett készült egy kísérleti kétkamerás teljes testes mód is guggolásra, előre hajolásra és alap lábmozgásra.

The main pipeline is:

```text
webcam or video
  -> OpenCV frame capture
  -> MediaPipe Pose upper-body landmarks
  -> shoulder / elbow / wrist extraction
  -> approximate arm-angle retargeting
  -> Unitree G1 arm qpos targets
  -> MuJoCo visualization
  -> OpenClaw-compatible command wrapper
```

The goal is visible, demonstrable imitation, not perfect humanoid whole-body control. The MVP tracks both human arms, computes approximate shoulder pitch, shoulder roll, and elbow flexion, then applies those targets to a Unitree G1 MuJoCo model.

## Magyar gyors útmutató

Röviden: a projekt célja, hogy kameraképből felismerje az ember mozgását, ebből kiszámolja a karok és a kísérleti teljes testes mód főbb szögeit, majd ezeket a Unitree G1 MuJoCo modellre küldje. A hangsúly nem a tökéletes robotdinamikán van, hanem azon, hogy a zsűri előtt stabilan és látványosan bemutatható legyen a valós emberi mozgás szimulációs utánzása.

Friss Windows gépen a legegyszerűbb indítás:

```powershell
.\FIRST_RUN_WINDOWS.bat
```

Ez létrehozza a Python virtuális környezetet, telepíti a függőségeket, letölti a Unitree MuJoCo asseteket, majd lefuttat egy státuszellenőrzést.

Ha a kameraállás változott, először kalibrálni kell:

```powershell
.\CALIBRATION_MENU.bat
```

A javasolt kalibrációs sorrend: régi képek törlése, új ChArUco képpárok felvétele, gyenge képek kiszűrése, majd stereo kalibráció számítása. A kalibráció azért fontos, mert a két kamera helyzete és látószöge gépenként és elhelyezésenként eltér.

A demó indítása:

```powershell
.\START_DEMO.bat
```

A menüben az `1` a stabil, beadáshoz ajánlott kétkaros demó. A `2` a kísérleti teljes testes mód, amely guggolást, előre hajolást és alap lábmozgást próbál követni két kamera alapján.

Ha valaki másik gépen tölti le a GitHub repót, nem kell VS Code-ot használnia. Elég a `FIRST_RUN_WINDOWS.bat`, majd szükség esetén a `CALIBRATION_MENU.bat` és végül a `START_DEMO.bat`. Más kamera esetén a kamera indexek és a kalibrációs fájl frissítése szükséges lehet.

Fontos korlát: ez nem valódi robotvezérlés, hanem MuJoCo szimuláció. A retargeting közelítő geometriai számításokat használ, ezért zajos kamera, kitakarás vagy rossz kalibráció esetén a mozgás pontatlanabb lehet.

## Részletes magyar magyarázat

A rendszer három fő részből áll. Az első rész a kameraoldal: az OpenCV megnyitja a webkamerát vagy a videófájlt, a MediaPipe Pose pedig megkeresi az emberi testpontokat. A stabil beadási módban főleg a váll, könyök és csukló pontok fontosak, mert ezekből számoljuk a két kar mozgását. A kísérleti teljes testes módban a csípő, térd, boka és törzs pontok is bekerülnek a számításba.

A második rész a retargeting. Ez azt jelenti, hogy az ember testpontjaiból robot ízületi célértékeket számolunk. Például a váll és könyök közti vektor adja a felkar irányát, a könyök és csukló közti vektor az alkar irányát, ezekből pedig közelítő váll- és könyökszögek számolhatók. A rendszer simítást és limitálást is használ, hogy a robotkar ne rángasson, és ne menjen irreális ízületi tartományba.

A harmadik rész a MuJoCo szimuláció. A program betölti a Unitree G1 robot XML modelljét, megkeresi a konfigurációban megadott kar-, törzs- és lábízületeket, majd ezekhez beállítja a számolt célpozíciókat. Az MVP-ben ez direkt `qpos` vezérléssel történik, mert látványos és stabil bemutatót ad. Ez később lecserélhető lenne fizikai PD/actuator vezérlésre.

A Unitree G1 assetek azért nincsenek közvetlenül a repóban, mert nagyok és külső forrásból származnak. A `FIRST_RUN_WINDOWS.bat` vagy a `DOWNLOAD_UNITREE_ASSETS.bat` letölti őket az `assets/unitree_mujoco` mappába. A GitHub repó így tiszta marad, de egy új gépen is automatikusan előkészíthető.

A kalibráció csak a kétkamerás módhoz szükséges. Ilyenkor a ChArUco tábla alapján a program kiszámolja, hogyan helyezkedik el a laptopkamera és az USB kamera egymáshoz képest. Ez adja a mélységi információt. Ha a kamerákat elmozdítod, elforgatod, másik gépre dugod, vagy más kamerát használsz, új kalibráció javasolt.

A beadáshoz a legbiztosabb indító a `START_DEMO.bat`, azon belül az `1` opció. Ez a stabil kétkaros verziót indítja. A `2` opció a teljes testes kísérleti verzió, ami látványosabb lehet, de érzékenyebb a kameraállásra és a teljes test láthatóságára.

Az OpenClaw wrapper szerepe, hogy a projekt ne csak külön Python fájlokból álljon, hanem legyen egy egységes parancsrétege. A `src/openclaw_real2sim_tool.py` olyan parancsokat ad, mint a `status`, `run-demo`, `calibrate` és `record-demo`. Ezt egy külső command-wrapper rendszer, például OpenClaw, könnyen meg tudja hívni.

Demo videóhoz érdemes egy képernyőfelvételt készíteni, ahol egyszerre látszik a kamera skeleton overlay és a MuJoCo G1 robot. A videóban mutasd meg a stabil kétkaros követést, majd opcionálisan a kísérleti teljes testes módot is. A dokumentációhoz készült magyar videószöveg a `docs/video_script_hu.txt` fájlban található.

## Project Layout / Projekt felépítése

```text
real2sim-g1/
|-- configs/g1_arm_mapping.yaml
|-- src/
|   |-- real2sim_app.py
|   |-- camera_pose.py
|   |-- retarget.py
|   |-- mujoco_g1.py
|   |-- openclaw_real2sim_tool.py
|   `-- utils.py
|-- scripts/
|   |-- print_g1_joints.py
|   |-- test_mujoco_g1.py
|   |-- test_pose_camera.py
|   `-- record_demo.py
|-- docs/
`-- media/
```

## Installation / Telepítés

Use Python 3.10 or newer. Python 3.10/3.11 is recommended because MediaPipe wheels are usually easiest there.

### Fresh Windows Clone / Friss Windows letöltés

After cloning or downloading the repository, run:

```powershell
.\FIRST_RUN_WINDOWS.bat
```

This creates `.venv`, installs `requirements.txt`, downloads the Unitree MuJoCo assets into `assets/unitree_mujoco`, and runs the status check.

The first-run setup also uses the custom ASCII SZTAKI/TTAH console banner for a polished competition-friendly startup.

VS Code is optional. The project can be operated from PowerShell or by double-clicking the `.bat` launchers:

```powershell
.\CHECK_READY.bat
.\CALIBRATION_MENU.bat
.\START_DEMO.bat
```

Important: a fresh clone still needs camera-specific stereo calibration. Run `CALIBRATION_MENU.bat` for the current camera placement before using the stereo demo on a different machine or after moving/rotating cameras.

### Manual Setup / Kézi telepítés

```bash
cd real2sim-g1
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Linux/macOS, activate with:

```bash
source .venv/bin/activate
```

## Unitree G1 MuJoCo Model / Unitree G1 MuJoCo modell

The Unitree G1 model is not vendored in this repository. Download it from Unitree's MuJoCo assets repository, then either place it at the default path or update the config.

On Windows, the easiest path is:

```powershell
.\DOWNLOAD_UNITREE_ASSETS.bat
```

Recommended local layout:

```text
real2sim-g1/
`-- assets/
    `-- unitree_mujoco/
        `-- unitree_robots/
            `-- g1/
                `-- scene.xml
```

Typical setup:

```bash
mkdir assets
git clone https://github.com/unitreerobotics/unitree_mujoco.git assets/unitree_mujoco
```

Then verify the XML path in:

```text
configs/g1_arm_mapping.yaml
```

You can also override the XML path at runtime:

```bash
python src/real2sim_app.py --config configs/g1_arm_mapping.yaml --model-xml path/to/g1/scene.xml
```

The included joint names are common G1-style names, but model revisions can differ. Print the actual model joints and update `joint_mapping` if needed:

```bash
python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
```

## Validation Commands / Ellenőrző parancsok

Check camera pose detection only:

```bash
python scripts/test_pose_camera.py
```

Print G1 joints and actuators:

```bash
python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
```

Load G1 and move both arms with a sinusoidal test:

```bash
python scripts/test_mujoco_g1.py --config configs/g1_arm_mapping.yaml
```

Experimental torso/leg mapping sanity test:

```bash
python scripts/test_mujoco_full_body.py --config configs/g1_arm_mapping.yaml
```

By default the MuJoCo controller uses stable direct-qpos visualization. This is intentional for the MVP because the downloaded G1 has a floating base and full physics can become unstable when arm joints are teleported every frame. To experiment with physics stepping, add `--advance-physics`.

Run the full webcam real2sim pipeline:

```bash
python src/real2sim_app.py --config configs/g1_arm_mapping.yaml --camera 0
```

Run from a recorded video:

```bash
python src/real2sim_app.py --config configs/g1_arm_mapping.yaml --video media/input_demo.mp4
```

Useful runtime controls:

```text
ESC or q  quit
c         recalibrate neutral pose from the current human pose
```

## Submission Launchers / Beadási indítók

For the competition demo, the project includes two Windows launchers:

```powershell
.\START_ARMS_ONLY.bat
.\START_FULL_BODY.bat
```

`START_ARMS_ONLY.bat` uses `configs/g1_arm_mapping_STABLE_ARMS.yaml` and only runs the stable two-arm imitation. This is the safest submission version.

`START_FULL_BODY.bat` uses `configs/g1_arm_mapping.yaml` and enables the experimental waist, leg, squat, bend, and root-motion demo.

You can also use the menu launcher:

```powershell
.\START_DEMO.bat
```

The demo launcher has a custom ASCII console banner based on `logo.png`, with SZTAKI/TTAH task labeling for the judges.

VS Code is not required to run the demos. Open PowerShell in the project folder, or double-click the `.bat` files from Windows Explorer.

## Recording A Demo / Demó videó rögzítése

Record the camera pose overlay while the MuJoCo viewer is running:

```bash
python scripts/record_demo.py --config configs/g1_arm_mapping.yaml --camera 0 --output media/demo_output.mp4
```

The script records the camera/skeleton overlay. For a polished competition video, record the desktop with the camera window and MuJoCo viewer side by side.

## OpenClaw Wrapper / OpenClaw parancsréteg

`src/openclaw_real2sim_tool.py` is a minimal OpenClaw-compatible command wrapper. It exposes stable commands that call the underlying Python app:

```bash
python src/openclaw_real2sim_tool.py status
python src/openclaw_real2sim_tool.py start --camera 0
python src/openclaw_real2sim_tool.py calibrate --camera 0
python src/openclaw_real2sim_tool.py run-demo --camera 0
python src/openclaw_real2sim_tool.py record-demo --camera 0 --output media/demo_output.mp4
```

OpenClaw can invoke the wrapper as a command-line tool, passing one of:

```text
start | calibrate | status | run-demo | record-demo
```

The `status` command checks Python package availability, the config file, the configured G1 XML path, and the configured camera.

## Optional Stereo ChArUco Calibration / Opcionális stereo ChArUco kalibráció

If two cameras are available, use the laptop camera as `0` and the USB camera as `1`. Camera `2` can be ignored if it is only a duplicate of the USB feed.

Preview cameras:

```bash
python scripts/preview_cameras.py --cameras 0 1 2 --backend dshow
```

Before recording a fresh calibration set, clear old ChArUco image pairs so the old and new captures do not mix:

```bash
python scripts/clear_stereo_charuco.py --yes
```

On Windows you can also run:

```powershell
.\CLEAR_CALIBRATION_IMAGES.bat
```

Capture ChArUco stereo pairs:

```bash
python scripts/capture_stereo_charuco.py
```

or on Windows:

```powershell
.\CAPTURE_CALIBRATION_IMAGES.bat
```

The capture script reads camera defaults from `configs/g1_arm_mapping.yaml`, including `left_camera`, `right_camera`, backend, resolution, and camera rotations. For the current setup, the USB/right camera is rotated with `right_rotation: "cw"`.

Move the board around the shared view and press Space when both sides say `READY`. Capture about 20-30 pairs.

After capture, remove weak pairs where either camera detected fewer than 12 ChArUco corners:

```bash
python scripts/filter_stereo_charuco.py --min-corners 12 --yes
```

or on Windows:

```powershell
.\FILTER_WEAK_CALIBRATION_IMAGES.bat
```

Then calibrate:

```bash
python scripts/calibrate_stereo_charuco.py --input-dir data/stereo_charuco --output configs/stereo_calibration.yaml
```

or on Windows:

```powershell
.\RUN_STEREO_CALIBRATION.bat
```

The complete Windows calibration menu is:

```powershell
.\CALIBRATION_MENU.bat
```

The menu uses a custom ASCII console banner based on `logo.png`, with SZTAKI/TTAH task labeling for the competition demo.

Menu steps:

```text
1  Clear old calibration images
2  Capture new ChArUco image pairs
3  Delete weak pairs below 12 corners
4  Compute stereo calibration
5  Exit
```

For best scale, measure one printed ChArUco square and pass it as meters, for example:

```bash
python scripts/calibrate_stereo_charuco.py --square-length-m 0.040 --marker-length-m 0.0299
```

Preview triangulated 3D pose:

```bash
python scripts/test_stereo_pose.py --stereo-config configs/stereo_calibration.yaml --left-camera 0 --right-camera 1
```

Run the real2sim demo using stereo 3D landmarks:

```bash
python src/openclaw_real2sim_tool.py run-demo --stereo --stereo-config configs/stereo_calibration.yaml --left-camera 0 --right-camera 1 --display-scale 0.5
```

Run the experimental torso/leg version:

```bash
python src/openclaw_real2sim_tool.py run-demo --stereo --full-body --stereo-config configs/stereo_calibration.yaml --left-camera 0 --right-camera 1 --display-scale 0.5
```

Run the experimental basic locomotion visualization:

```bash
python src/openclaw_real2sim_tool.py run-demo --stereo --full-body --locomotion-demo --stereo-config configs/stereo_calibration.yaml --left-camera 0 --right-camera 1 --display-scale 0.5
```

This is visual root motion only: small stepping, weight shift, and turning. It is not a balanced walking controller.

Use `--display-scale 0.5` or `--display-scale 0.6` on a single monitor if the camera preview covers the MuJoCo window.

## Configuration / Konfiguráció

Main config:

```text
configs/g1_arm_mapping.yaml
```

Important sections:

```yaml
model:
  xml_path: "assets/unitree_mujoco/unitree_robots/g1/scene.xml"

retargeting:
  smoothing_alpha: 0.25
  confidence_threshold: 0.5
  use_neutral_calibration: true

joint_mapping:
  left_shoulder_pitch: "left_shoulder_pitch_joint"
  left_shoulder_roll: "left_shoulder_roll_joint"
  left_elbow: "left_elbow_joint"
  right_shoulder_pitch: "right_shoulder_pitch_joint"
  right_shoulder_roll: "right_shoulder_roll_joint"
  right_elbow: "right_elbow_joint"
```

If the robot moves in the opposite direction for one joint, adjust the `retargeting.signs` or `retargeting.offsets` values.
Use `retargeting.scales` to reduce overly large motions without changing the underlying pose geometry.

## Known Limitations / Ismert korlátok

- Arm retargeting is approximate and uses simple geometric angles.
- Single-camera pose estimation is noisy and can fail under occlusion.
- MediaPipe coordinates are not calibrated metric 3D measurements.
- Human and Unitree G1 arm kinematics do not match perfectly.
- The current MuJoCo mode directly sets arm joint `qpos` targets for demonstration.
- This MVP does not control a real robot.

More detail is in [docs/limitations.md](docs/limitations.md).

## License / Licenc

This repository includes a Creative Commons Attribution 4.0 International license notice in [LICENSE](LICENSE), as requested by the competition. Documentation, diagrams, and demo materials are intended to be CC BY 4.0 licensed. Creative Commons is not the usual first choice for source code licensing, but the project is marked this way to satisfy the competition deliverable.

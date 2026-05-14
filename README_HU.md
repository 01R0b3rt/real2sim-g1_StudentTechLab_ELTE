# Real2Sim G1 - StudentTechLab ELTE

**Nyelv:** [English](README.md) | [Magyar](README_HU.md)

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

## Projekt célja

Ez a projekt egy gyakorlati MVP egy real-to-simulation robotikai versenyfeladathoz. A rendszer kameraképből felismeri az emberi testpontokat, a karok és a test mozgását egyszerű retargeting logikával robot ízületi célokra képezi le, majd a Unitree G1 humanoid modellt MuJoCo szimulátorban mozgatja.

A beadáshoz legbiztosabb mód a stabil kétkaros utánzás. Emellett készült egy kísérleti kétkamerás teljes testes mód is guggolásra, előre hajolásra, alap lábmozgásra és vizuális helyváltoztatásra.

```text
webkamera vagy videó
  -> OpenCV képkocka beolvasás
  -> MediaPipe Pose testpont felismerés
  -> váll / könyök / csukló pontok kinyerése
  -> közelítő karszög-számítás
  -> Unitree G1 ízületi célértékek
  -> MuJoCo vizualizáció
  -> OpenClaw-kompatibilis parancsréteg
```

A cél nem a tökéletes humanoid vezérlés, hanem egy stabilan bemutatható, látványos real2sim pipeline.

## Hogyan működik?

A rendszer három fő részből áll.

Az első rész a kameraoldal. Az OpenCV megnyitja a webkamerát vagy egy videófájlt, a MediaPipe Pose pedig megkeresi az emberi testpontokat. A stabil beadási módban főleg a váll, könyök és csukló pontok fontosak, mert ezekből számoljuk a két kar mozgását. A kísérleti teljes testes módban a csípő, térd, boka és törzs pontok is bekerülnek a számításba.

A második rész a retargeting. Ez azt jelenti, hogy az ember testpontjaiból robot ízületi célértékeket számolunk. Például a váll és könyök közti vektor adja a felkar irányát, a könyök és csukló közti vektor az alkar irányát, ezekből pedig közelítő váll- és könyökszögek számolhatók. A rendszer simítást és limitálást is használ, hogy a robotkar ne rángasson, és ne menjen irreális ízületi tartományba.

A harmadik rész a MuJoCo szimuláció. A program betölti a Unitree G1 robot XML modelljét, megkeresi a konfigurációban megadott kar-, törzs- és lábízületeket, majd ezekhez beállítja a számolt célpozíciókat. Az MVP direkt `qpos` vezérlést használ, mert látványos és stabil bemutatót ad. Később ez lecserélhető lenne fizikai PD/actuator vezérlésre.

## Projekt felépítése

```text
real2sim-g1/
|-- configs/
|   |-- g1_arm_mapping.yaml
|   `-- g1_arm_mapping_STABLE_ARMS.yaml
|-- src/
|   |-- real2sim_app.py
|   |-- camera_pose.py
|   |-- stereo_pose.py
|   |-- retarget.py
|   |-- mujoco_g1.py
|   |-- openclaw_real2sim_tool.py
|   `-- utils.py
|-- scripts/
|-- docs/
|-- media/
|-- FIRST_RUN_WINDOWS.bat
|-- CALIBRATION_MENU.bat
|-- START_DEMO.bat
|-- START_ARMS_ONLY.bat
`-- START_FULL_BODY.bat
```

## Gyors indítás Windows alatt

Friss letöltés után indítsd ezt:

```powershell
.\FIRST_RUN_WINDOWS.bat
```

Ez létrehozza a Python virtuális környezetet, telepíti a függőségeket, letölti a Unitree MuJoCo asseteket, majd lefuttat egy státuszellenőrzést.

Ezután indítsd a demómenüt:

```powershell
.\START_DEMO.bat
```

A menü opciói:

```text
1  Stabil kétkaros demó beadáshoz
2  Kísérleti teljes testes demó
3  Kilépés
```

VS Code nem kötelező. A projekt PowerShellből vagy a `.bat` fájlokra kattintva is futtatható.

## Unitree G1 MuJoCo modell

A Unitree G1 modell nincs közvetlenül a repóban, mert nagy méretű külső asset. Letöltéshez használd:

```powershell
.\DOWNLOAD_UNITREE_ASSETS.bat
```

Az elvárt lokális mappaszerkezet:

```text
real2sim-g1/
`-- assets/
    `-- unitree_mujoco/
        `-- unitree_robots/
            `-- g1/
                `-- scene.xml
```

Az alapértelmezett modellútvonal itt állítható:

```text
configs/g1_arm_mapping.yaml
```

A tényleges robotízületek és actuatorok listázása:

```bash
python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
```

## Kézi telepítés

```bash
cd real2sim-g1
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS alatt:

```bash
source .venv/bin/activate
```

## Ellenőrző parancsok

Csak kamera és pózfelismerés tesztelése:

```bash
python scripts/test_pose_camera.py
```

Unitree G1 ízületek és actuatorok kiírása:

```bash
python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
```

G1 modell betöltése és kétkaros sinus mozgásteszt:

```bash
python scripts/test_mujoco_g1.py --config configs/g1_arm_mapping.yaml
```

Teljes webkamerás real2sim pipeline:

```bash
python src/real2sim_app.py --config configs/g1_arm_mapping.yaml --camera 0
```

Futtatás rögzített videóból:

```bash
python src/real2sim_app.py --config configs/g1_arm_mapping.yaml --video media/input_demo.mp4
```

Futás közbeni vezérlés:

```text
ESC vagy q  kilépés
c           neutrális póz újrakalibrálása az aktuális emberi pózból
```

## Beadási indítók

Közvetlen Windows indítók:

```powershell
.\START_ARMS_ONLY.bat
.\START_FULL_BODY.bat
```

`START_ARMS_ONLY.bat`: a stabil kétkaros utánzást indítja a `configs/g1_arm_mapping_STABLE_ARMS.yaml` beállítással. Ez a legbiztosabb beadási verzió.

`START_FULL_BODY.bat`: a kísérleti teljes testes módot indítja törzs-, láb-, guggolás-, előrehajlás- és vizuális helyváltoztatás-támogatással.

Menüs indító:

```powershell
.\START_DEMO.bat
```

## OpenClaw parancsréteg

A `src/openclaw_real2sim_tool.py` egy minimális OpenClaw-kompatibilis wrapper. Egységes parancsokat ad a rendszerhez:

```bash
python src/openclaw_real2sim_tool.py status
python src/openclaw_real2sim_tool.py start --camera 0
python src/openclaw_real2sim_tool.py calibrate --camera 0
python src/openclaw_real2sim_tool.py run-demo --camera 0
python src/openclaw_real2sim_tool.py record-demo --camera 0 --output media/demo_output.mp4
```

A `status` parancs ellenőrzi a Python csomagokat, a config fájlt, a G1 XML útvonalat és a kamerát.

## Stereo ChArUco kalibráció

A stereo kalibráció csak a kétkamerás/teljes testes módhoz szükséges. Ha a kamerákat elmozdítod, elforgatod, másik gépre dugod, vagy más kamerát használsz, új kalibráció ajánlott.

Windows menü:

```powershell
.\CALIBRATION_MENU.bat
```

Javasolt sorrend:

```text
1  Régi kalibrációs képek törlése
2  Új ChArUco képpárok felvétele
3  Gyenge képpárok törlése 12 sarok alatt
4  Stereo kalibráció számítása
5  Kilépés
```

Kamerák előnézete:

```bash
python scripts/preview_cameras.py --cameras 0 1 2 --backend dshow
```

ChArUco képpárok felvétele:

```bash
python scripts/capture_stereo_charuco.py
```

Gyenge képpárok kiszűrése:

```bash
python scripts/filter_stereo_charuco.py --min-corners 12 --yes
```

Stereo kalibráció számítása:

```bash
python scripts/calibrate_stereo_charuco.py --input-dir data/stereo_charuco --output configs/stereo_calibration.yaml
```

Kísérleti teljes testes stereo demó:

```bash
python src/openclaw_real2sim_tool.py run-demo --stereo --full-body --locomotion-demo --stereo-config configs/stereo_calibration.yaml --left-camera 0 --right-camera 1 --display-scale 0.5
```

## Demó videó rögzítése

Kamera skeleton overlay rögzítése MuJoCo futás közben:

```bash
python scripts/record_demo.py --config configs/g1_arm_mapping.yaml --camera 0 --output media/demo_output.mp4
```

Beadáshoz érdemes képernyőfelvételt készíteni, ahol egyszerre látszik a kamera/skeleton ablak és a MuJoCo G1 robot.

A magyar videószöveg itt található:

```text
docs/video_script_hu.txt
```

## Konfiguráció

Fő config:

```text
configs/g1_arm_mapping.yaml
```

Fontos részek:

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

Ha egy ízület fordítva mozog, a `retargeting.signs` vagy `retargeting.offsets` értékeket kell állítani. A `retargeting.scales` a mozgás amplitúdójának csökkentésére használható.

## Ismert korlátok

- A retargeting közelítő geometriai számításokat használ.
- Az egykamerás pózfelismerés zajos lehet és kitakarásnál hibázhat.
- A stereo kalibráció erősen függ a kamerák elhelyezésétől és a ChArUco képek minőségétől.
- Az emberi test és a Unitree G1 kinematikája nem egyezik tökéletesen.
- Az MVP stabil bemutató miatt direkt MuJoCo `qpos` célértékeket használ.
- A projekt nem vezérel valódi robotot.

Részletesebb lista: [docs/limitations.md](docs/limitations.md).

## Szerző

StudentTechLab ELTE

GitHub: [01R0b3rt](https://github.com/01R0b3rt)

Projekt repó: [real2sim-g1_StudentTechLab_ELTE](https://github.com/01R0b3rt/real2sim-g1_StudentTechLab_ELTE)

## Licenc

A repó Creative Commons Attribution 4.0 International licencértesítést tartalmaz a [LICENSE](LICENSE) fájlban, mert a verseny ezt kérte. A dokumentáció, diagramok és demóanyagok CC BY 4.0 jelölést kapnak. A Creative Commons nem ideális forráskódlicenc, de a projekt így teljesíti a verseny által kért licencmegjelölést.

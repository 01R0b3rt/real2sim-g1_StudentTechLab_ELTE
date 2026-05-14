# Real2Sim G1 - StudentTechLab ELTE

**Language:** [English](README.md) | [Magyar](README_HU.md)

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

## Project Purpose

This repository contains a practical MVP for a real-to-simulation robotics competition task. A camera observes human upper-body motion, MediaPipe extracts body landmarks, and a Unitree G1 humanoid model in MuJoCo imitates the detected movement.

The stable submission mode focuses on robust two-arm imitation. The repository also includes an experimental stereo full-body mode for squatting, leaning, basic leg movement, and visual root-motion demos.

```text
webcam or video
  -> OpenCV frame capture
  -> MediaPipe Pose landmarks
  -> shoulder / elbow / wrist extraction
  -> approximate arm-angle retargeting
  -> Unitree G1 qpos targets
  -> MuJoCo visualization
  -> OpenClaw-compatible command wrapper
```

The goal is visible, demonstrable imitation rather than perfect humanoid whole-body control.

## Project Layout

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

## Quick Start On Windows

After cloning or downloading the repository, run:

```powershell
.\FIRST_RUN_WINDOWS.bat
```

This creates `.venv`, installs Python dependencies, downloads the Unitree MuJoCo assets into `assets/unitree_mujoco`, and runs a status check.

Then run the demo launcher:

```powershell
.\START_DEMO.bat
```

Launcher options:

```text
1  Stable two-arm demo for submission
2  Experimental full-body demo
3  Exit
```

VS Code is optional. The project can be run from PowerShell or by double-clicking the `.bat` launchers.

## Unitree G1 MuJoCo Model

The Unitree G1 model is not stored directly in this repository because it is a large external asset. Use:

```powershell
.\DOWNLOAD_UNITREE_ASSETS.bat
```

Expected local layout:

```text
real2sim-g1/
`-- assets/
    `-- unitree_mujoco/
        `-- unitree_robots/
            `-- g1/
                `-- scene.xml
```

The default model path is configured in:

```text
configs/g1_arm_mapping.yaml
```

You can inspect the actual joint and actuator names with:

```bash
python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
```

## Manual Setup

```bash
cd real2sim-g1
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

## Validation Commands

Check camera pose detection:

```bash
python scripts/test_pose_camera.py
```

Print Unitree G1 joints and actuators:

```bash
python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
```

Load G1 and move both arms with a simple sinusoidal test:

```bash
python scripts/test_mujoco_g1.py --config configs/g1_arm_mapping.yaml
```

Run the full webcam pipeline:

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

## Submission Launchers

The project includes two direct Windows launchers:

```powershell
.\START_ARMS_ONLY.bat
.\START_FULL_BODY.bat
```

`START_ARMS_ONLY.bat` uses `configs/g1_arm_mapping_STABLE_ARMS.yaml` and runs only the stable two-arm imitation. This is the safest version for the final submission.

`START_FULL_BODY.bat` uses `configs/g1_arm_mapping.yaml` and enables the experimental waist, leg, squat, bend, and visual locomotion mode.

The menu launcher is:

```powershell
.\START_DEMO.bat
```

## OpenClaw Wrapper

`src/openclaw_real2sim_tool.py` is a minimal OpenClaw-compatible command wrapper. It exposes stable CLI commands that call the underlying Python app:

```bash
python src/openclaw_real2sim_tool.py status
python src/openclaw_real2sim_tool.py start --camera 0
python src/openclaw_real2sim_tool.py calibrate --camera 0
python src/openclaw_real2sim_tool.py run-demo --camera 0
python src/openclaw_real2sim_tool.py record-demo --camera 0 --output media/demo_output.mp4
```

The `status` command checks Python package availability, the config file, the configured G1 XML path, and the configured camera.

## Stereo ChArUco Calibration

Stereo calibration is only needed for the two-camera/full-body mode. If the cameras are moved, rotated, replaced, or connected to a different computer, run a new calibration.

Windows menu:

```powershell
.\CALIBRATION_MENU.bat
```

Recommended flow:

```text
1  Clear old calibration images
2  Capture new ChArUco image pairs
3  Delete weak pairs below 12 corners
4  Compute stereo calibration
5  Exit
```

Preview cameras:

```bash
python scripts/preview_cameras.py --cameras 0 1 2 --backend dshow
```

Capture ChArUco stereo pairs:

```bash
python scripts/capture_stereo_charuco.py
```

Filter weak image pairs:

```bash
python scripts/filter_stereo_charuco.py --min-corners 12 --yes
```

Compute stereo calibration:

```bash
python scripts/calibrate_stereo_charuco.py --input-dir data/stereo_charuco --output configs/stereo_calibration.yaml
```

Run the experimental stereo full-body demo:

```bash
python src/openclaw_real2sim_tool.py run-demo --stereo --full-body --locomotion-demo --stereo-config configs/stereo_calibration.yaml --left-camera 0 --right-camera 1 --display-scale 0.5
```

## Demo Recording

Record the camera pose overlay while MuJoCo is running:

```bash
python scripts/record_demo.py --config configs/g1_arm_mapping.yaml --camera 0 --output media/demo_output.mp4
```

For a polished competition video, record the desktop with the camera/skeleton window and the MuJoCo viewer visible side by side.

## Configuration

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

If a robot joint moves in the wrong direction, adjust `retargeting.signs` or `retargeting.offsets`. Use `retargeting.scales` to reduce motion amplitude.

## Known Limitations

- Retargeting is approximate and uses simple geometric angles.
- Single-camera pose estimation is noisy and can fail under occlusion.
- Stereo calibration depends strongly on camera placement and ChArUco image quality.
- Human and Unitree G1 kinematics do not match perfectly.
- The MVP uses direct MuJoCo `qpos` targets for demonstration stability.
- This project does not control a real robot.

More detail is available in [docs/limitations.md](docs/limitations.md).

## License

This repository includes a Creative Commons Attribution 4.0 International license notice in [LICENSE](LICENSE), as requested by the competition. Documentation, diagrams, and demo materials are intended to be CC BY 4.0 licensed. Creative Commons is not the usual first choice for source code licensing, but the project is marked this way to satisfy the competition deliverable.

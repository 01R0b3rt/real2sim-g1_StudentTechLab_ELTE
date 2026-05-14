# Architecture

The project is intentionally small and modular. Each module can be tested alone before running the full real2sim loop.

```text
Camera/video source
  |
  v
src/camera_pose.py
  - Opens webcam or video with OpenCV
  - Runs MediaPipe Pose
  - Extracts shoulders, elbows, wrists, and hips
  - Draws a debug skeleton overlay
  |
  v
src/retarget.py
  - Builds an approximate torso coordinate frame
  - Computes upper-arm and forearm vectors
  - Estimates shoulder pitch, shoulder roll, and elbow flexion
  - Applies neutral calibration, signs, offsets, smoothing, and limits
  |
  v
src/mujoco_g1.py
  - Loads the configured Unitree G1 MuJoCo XML
  - Builds a joint-name to qpos-index map
  - Applies arm targets directly to qpos for the MVP
  - Steps and renders the MuJoCo simulation
  |
  v
src/real2sim_app.py
  - Owns the runtime loop
  - Holds the previous target when pose detection fails
  - Handles calibration, debug windows, and optional recording
```

Optional stereo calibration utilities sit around the runtime loop:

```text
scripts/clear_stereo_charuco.py
  - Deletes or archives old left_*.png/right_*.png calibration captures
  - Prevents old and new ChArUco image sets from mixing

scripts/capture_stereo_charuco.py
  - Captures synchronized left/right ChArUco image pairs
  - Reads camera defaults and rotations from configs/g1_arm_mapping.yaml

scripts/filter_stereo_charuco.py
  - Re-detects ChArUco corners in saved stereo pairs
  - Deletes or archives pairs where either side has fewer than the chosen minimum, usually 12

scripts/calibrate_stereo_charuco.py
  - Computes stereo camera matrices, distortion, rotation, translation, and baseline
  - Writes configs/stereo_calibration.yaml
```

## Pose Data

The required landmarks are:

```text
left_shoulder, left_elbow, left_wrist
right_shoulder, right_elbow, right_wrist
left_hip, right_hip
```

Each landmark is represented as a normalized MediaPipe vector:

```text
[x, y, z]
```

Visibility is checked for every required upper-body landmark. If any required landmark is below the configured confidence threshold, the frame is ignored and the robot holds the previous valid target.

## Retargeting

The torso frame is estimated from shoulders and hips:

```text
torso_up      = normalize(shoulder_center - hip_center)
torso_right   = normalize(right_shoulder - left_shoulder)
torso_forward = normalize(cross(torso_right, torso_up))
```

For each arm:

```text
upper_arm = elbow - shoulder
forearm   = wrist - elbow
```

The upper-arm vector is projected into the torso frame. The MVP uses:

```text
shoulder_pitch = atan2(forward_component, down_component)
shoulder_roll  = atan2(side_component, down_component)
elbow_flexion  = pi - angle_between(-upper_arm, forearm)
```

This is not a calibrated biomechanical model. It is a visible, tunable approximation that is easy to explain during a demo.

## MuJoCo Control

The first implementation directly writes selected arm joint `qpos` values:

```text
target name -> YAML joint_mapping -> MuJoCo joint name -> qpos index
```

This keeps the MVP robust for visualization. The controller is separated in `src/mujoco_g1.py` so actuator or PD control can replace direct qpos setting later.

## OpenClaw Interface

The OpenClaw-facing layer is a command wrapper:

```text
src/openclaw_real2sim_tool.py status
src/openclaw_real2sim_tool.py start
src/openclaw_real2sim_tool.py calibrate
src/openclaw_real2sim_tool.py run-demo
src/openclaw_real2sim_tool.py record-demo
```

The wrapper does not hide the Python implementation. It gives OpenClaw stable commands to call and gives humans the same entry points for validation.

## Calibration Image Cleanup

Fresh stereo calibration should start from a clean image folder:

```bash
python scripts/clear_stereo_charuco.py --yes
```

The script only affects generated ChArUco capture files:

```text
data/stereo_charuco/left_*.png
data/stereo_charuco/right_*.png
```

For safety, it supports:

```bash
python scripts/clear_stereo_charuco.py --dry-run
python scripts/clear_stereo_charuco.py --archive --yes
```

After capture, weak stereo pairs can be removed before running calibration:

```bash
python scripts/filter_stereo_charuco.py --min-corners 12 --yes
```

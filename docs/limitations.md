# Limitations

This MVP is designed to be demonstrable, not physically perfect.

## Approximate Retargeting

The shoulder and elbow targets are estimated from simple vector geometry. The system does not solve full inverse kinematics and does not model all anatomical degrees of freedom.

## Camera Occlusion

A single webcam can lose wrists, elbows, or shoulders when arms cross the body, leave the frame, or are hidden behind objects. When confidence drops below the configured threshold, the robot holds the previous valid pose.

## Noisy Pose Detection

MediaPipe landmarks are normalized image-space estimates. They are not calibrated metric 3D points, so depth motion and forward/backward arm movement are approximate.

## Calibration Data Hygiene

Stereo calibration quality depends on using one consistent set of ChArUco captures. Old `left_*.png` and `right_*.png` files should be deleted or archived before recording a new calibration set:

```bash
python scripts/clear_stereo_charuco.py --yes
```

Weak pairs where either side detects fewer than 12 ChArUco corners should be filtered before calibration:

```bash
python scripts/filter_stereo_charuco.py --min-corners 12 --yes
```

If old and new captures are mixed after moving or rotating the cameras, the stereo calibration can produce a wrong baseline or unstable 3D landmarks.

## Robot-Human Kinematic Mismatch

Human shoulder/elbow motion does not map perfectly to the Unitree G1 joint layout. The YAML `signs`, `offsets`, and `joint_limits` fields are included so the mapping can be tuned after inspecting the exact MuJoCo model revision.

## Direct qpos Control

The current MuJoCo controller directly sets selected arm joint positions. This is useful for a robust visual MVP, but it is not a physics-faithful actuator controller. The code is separated so a future PD or actuator-control mode can replace it.

## No Real Robot Control

This project only controls a Unitree G1 model in MuJoCo. It does not send commands to physical robot hardware.

## Minimal OpenClaw Integration

The OpenClaw layer is a command wrapper with stable subcommands. It is intentionally minimal and demonstrable; deeper OpenClaw-native schemas can be added later if the competition environment requires them.

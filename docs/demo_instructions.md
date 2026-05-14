# Demo Instructions

This is a 10-minute presentation flow for the MVP.

## Before The Demo

1. On a fresh Windows clone, run the first-time setup:

   ```powershell
   .\FIRST_RUN_WINDOWS.bat
   ```

   This creates `.venv`, installs dependencies, downloads Unitree MuJoCo assets, and runs a status check.

2. Install dependencies manually only if you are not using `FIRST_RUN_WINDOWS.bat`:

   ```bash
   pip install -r requirements.txt
   ```

3. Download the Unitree MuJoCo assets and make sure the configured XML exists:

   ```bash
   python src/openclaw_real2sim_tool.py status
   ```

4. Verify the model joint names:

   ```bash
   python scripts/print_g1_joints.py --model configs/g1_arm_mapping.yaml
   ```

5. If needed, update `configs/g1_arm_mapping.yaml`.

6. Test camera pose detection:

   ```bash
   python scripts/test_pose_camera.py
   ```

7. Test MuJoCo arm movement:

   ```bash
   python scripts/test_mujoco_g1.py --config configs/g1_arm_mapping.yaml
   ```

8. If you are doing a fresh stereo calibration, clear old ChArUco image pairs before capturing new ones:

   ```powershell
   .\CLEAR_CALIBRATION_IMAGES.bat
   ```

   or:

   ```bash
   python scripts/clear_stereo_charuco.py --yes
   ```

   Use `--dry-run` first if you only want to check what would be deleted.

9. VS Code is optional. The Windows calibration workflow can be run from PowerShell or by double-clicking:

   ```powershell
   .\CALIBRATION_MENU.bat
   ```

   Individual steps are also available:

   ```powershell
   .\CAPTURE_CALIBRATION_IMAGES.bat
   .\FILTER_WEAK_CALIBRATION_IMAGES.bat
   .\RUN_STEREO_CALIBRATION.bat
   .\START_DEMO.bat
   ```

## Suggested 10-Minute Script

Minute 0-1: State the goal.

```text
The camera tracks human upper-body motion and retargets both arms to a Unitree G1 model in MuJoCo.
```

Minute 1-2: Show the project structure and config.

```text
configs/g1_arm_mapping.yaml controls the model path, camera source, joint mapping, limits, smoothing, and sign corrections.
```

Minute 2-3: Run status through the OpenClaw wrapper.

```bash
python src/openclaw_real2sim_tool.py status
```

Minute 3-4: Show camera pose validation.

```bash
python scripts/test_pose_camera.py
```

Minute 4-5: Mention stereo calibration hygiene and show MuJoCo model validation.

```bash
python scripts/clear_stereo_charuco.py --dry-run
```

```text
Before a new stereo calibration, old left_*.png/right_*.png image pairs are removed so old and new calibration sets do not mix.
After capture, weak pairs with fewer than 12 ChArUco corners on either side are removed before calibration.
```

```bash
python scripts/test_mujoco_g1.py --config configs/g1_arm_mapping.yaml
```

Minute 5-8: Run the full real2sim demo.

```bash
python src/openclaw_real2sim_tool.py run-demo --camera 0
```

Stand in view, hold a neutral pose for calibration, then move both arms slowly:

```text
raise/lower both arms
move arms sideways
bend/extend elbows
briefly occlude an arm to show stable hold behavior
```

Minute 8-9: Record or show the demo video.

```bash
python src/openclaw_real2sim_tool.py record-demo --camera 0 --output media/demo_output.mp4
```

Minute 9-10: Summarize limitations and next steps.

```text
The MVP uses direct qpos visualization and approximate retargeting. Next steps are actuator-level PD control, camera calibration, IK, and richer wrist/torso tracking.
```

## Presentation Tips

- Keep the person fully visible from hips to head.
- Use bright, even lighting.
- Wear sleeves that contrast with the background.
- Move slowly for the first run so smoothing and calibration are easy to see.
- Keep the MuJoCo viewer and camera debug window visible side by side.

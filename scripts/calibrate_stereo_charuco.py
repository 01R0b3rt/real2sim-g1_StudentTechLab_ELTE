from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate a stereo camera pair from ChArUco image pairs.")
    parser.add_argument("--input-dir", default="data/stereo_charuco", help="Directory with left_###.png/right_###.png.")
    parser.add_argument("--output", default="configs/stereo_calibration.yaml", help="Output YAML path.")
    parser.add_argument("--squares-x", type=int, default=5, help="ChArUco board squares across.")
    parser.add_argument("--squares-y", type=int, default=7, help="ChArUco board squares down.")
    parser.add_argument(
        "--square-length-m",
        type=float,
        default=0.040,
        help="Measured physical square side length in meters. Measure your printed/displayed board for best scale.",
    )
    parser.add_argument(
        "--marker-length-m",
        type=float,
        default=0.0299,
        help="Measured physical ArUco marker side length in meters.",
    )
    parser.add_argument("--dictionary", default="DICT_5X5_50", help="OpenCV aruco dictionary name.")
    parser.add_argument("--min-corners", type=int, default=8, help="Minimum corners per camera and shared pair.")
    return parser.parse_args()


def make_board(cv2, args: argparse.Namespace):
    dictionary_id = getattr(cv2.aruco, args.dictionary)
    dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
    board = cv2.aruco.CharucoBoard(
        (args.squares_x, args.squares_y),
        args.square_length_m,
        args.marker_length_m,
        dictionary,
    )
    return board, dictionary


def detect_charuco(cv2, image, board, dictionary):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    marker_corners, marker_ids, _ = detector.detectMarkers(gray)
    if marker_ids is None or len(marker_ids) == 0:
        return None, None

    count, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
        marker_corners,
        marker_ids,
        gray,
        board,
    )
    if charuco_corners is None or charuco_ids is None or count <= 0:
        return None, None
    return charuco_corners, charuco_ids


def matched_pair_points(cv2, board, corners_l, ids_l, corners_r, ids_r, min_corners: int):
    ids_l_flat = ids_l.flatten().astype(int)
    ids_r_flat = ids_r.flatten().astype(int)
    common_ids = sorted(set(ids_l_flat.tolist()) & set(ids_r_flat.tolist()))
    if len(common_ids) < min_corners:
        return None, None, None

    left_lookup = {int(marker_id): corners_l[i] for i, marker_id in enumerate(ids_l_flat)}
    right_lookup = {int(marker_id): corners_r[i] for i, marker_id in enumerate(ids_r_flat)}
    chessboard_corners = board.getChessboardCorners()

    object_points = []
    image_points_l = []
    image_points_r = []
    for marker_id in common_ids:
        object_points.append(chessboard_corners[marker_id])
        image_points_l.append(left_lookup[marker_id])
        image_points_r.append(right_lookup[marker_id])

    import numpy as np

    return (
        np.asarray(object_points, dtype="float32").reshape(-1, 1, 3),
        np.asarray(image_points_l, dtype="float32").reshape(-1, 1, 2),
        np.asarray(image_points_r, dtype="float32").reshape(-1, 1, 2),
    )


def as_list(value):
    return value.tolist() if hasattr(value, "tolist") else value


def main() -> int:
    try:
        import cv2
        import numpy as np
        import yaml
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run pip install -r requirements.txt first.")
        return 2

    args = parse_args()
    input_dir = (PROJECT_ROOT / args.input_dir).resolve()
    output_path = (PROJECT_ROOT / args.output).resolve()
    board, dictionary = make_board(cv2, args)

    left_paths = sorted(input_dir.glob("left_*.png"))
    pairs = []
    for left_path in left_paths:
        suffix = left_path.stem.split("_")[-1]
        right_path = input_dir / f"right_{suffix}.png"
        if right_path.exists():
            pairs.append((left_path, right_path))

    if len(pairs) < 8:
        print(f"Only found {len(pairs)} stereo pairs in {input_dir}. Capture at least 15-25 good pairs.")
        return 1

    all_corners_l = []
    all_ids_l = []
    all_corners_r = []
    all_ids_r = []
    stereo_object_points = []
    stereo_image_points_l = []
    stereo_image_points_r = []
    image_size_l = None
    image_size_r = None

    for left_path, right_path in pairs:
        image_l = cv2.imread(str(left_path))
        image_r = cv2.imread(str(right_path))
        if image_l is None or image_r is None:
            continue
        image_size_l = (image_l.shape[1], image_l.shape[0])
        image_size_r = (image_r.shape[1], image_r.shape[0])

        corners_l, ids_l = detect_charuco(cv2, image_l, board, dictionary)
        corners_r, ids_r = detect_charuco(cv2, image_r, board, dictionary)
        if corners_l is None or corners_r is None:
            print(f"skipping {left_path.name}: board not detected in both images")
            continue
        if len(ids_l) < args.min_corners or len(ids_r) < args.min_corners:
            print(f"skipping {left_path.name}: too few corners")
            continue

        all_corners_l.append(corners_l)
        all_ids_l.append(ids_l)
        all_corners_r.append(corners_r)
        all_ids_r.append(ids_r)

        obj, img_l, img_r = matched_pair_points(
            cv2,
            board,
            corners_l,
            ids_l,
            corners_r,
            ids_r,
            args.min_corners,
        )
        if obj is not None:
            stereo_object_points.append(obj)
            stereo_image_points_l.append(img_l)
            stereo_image_points_r.append(img_r)

    if image_size_l is None or image_size_r is None:
        print("No readable stereo images found.")
        return 1
    if len(stereo_object_points) < 8:
        print(f"Only {len(stereo_object_points)} usable stereo views. Capture more board positions.")
        return 1

    print(f"Calibrating left camera with {len(all_corners_l)} views...")
    ret_l, camera_l, dist_l, _, _ = cv2.aruco.calibrateCameraCharuco(
        all_corners_l,
        all_ids_l,
        board,
        image_size_l,
        None,
        None,
    )

    print(f"Calibrating right camera with {len(all_corners_r)} views...")
    ret_r, camera_r, dist_r, _, _ = cv2.aruco.calibrateCameraCharuco(
        all_corners_r,
        all_ids_r,
        board,
        image_size_r,
        None,
        None,
    )

    print(f"Stereo calibrating with {len(stereo_object_points)} matched views...")
    flags = cv2.CALIB_FIX_INTRINSIC
    stereo_ret, camera_l, dist_l, camera_r, dist_r, rotation, translation, essential, fundamental = cv2.stereoCalibrate(
        stereo_object_points,
        stereo_image_points_l,
        stereo_image_points_r,
        camera_l,
        dist_l,
        camera_r,
        dist_r,
        image_size_l,
        flags=flags,
    )

    output = {
        "cameras": {
            "left_index": 0,
            "right_index": 1,
            "left_image_width": image_size_l[0],
            "left_image_height": image_size_l[1],
            "right_image_width": image_size_r[0],
            "right_image_height": image_size_r[1],
        },
        "charuco": {
            "squares_x": args.squares_x,
            "squares_y": args.squares_y,
            "square_length_m": args.square_length_m,
            "marker_length_m": args.marker_length_m,
            "dictionary": args.dictionary,
        },
        "quality": {
            "left_reprojection_error": float(ret_l),
            "right_reprojection_error": float(ret_r),
            "stereo_reprojection_error": float(stereo_ret),
            "usable_stereo_views": len(stereo_object_points),
        },
        "left": {
            "camera_matrix": as_list(camera_l),
            "distortion": as_list(dist_l),
        },
        "right": {
            "camera_matrix": as_list(camera_r),
            "distortion": as_list(dist_r),
        },
        "stereo": {
            "rotation_left_to_right": as_list(rotation),
            "translation_left_to_right_m": as_list(translation),
            "essential": as_list(essential),
            "fundamental": as_list(fundamental),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(output, handle, sort_keys=False)

    print(f"Saved stereo calibration to: {output_path}")
    print(f"Left reprojection error:   {ret_l:.4f}")
    print(f"Right reprojection error:  {ret_r:.4f}")
    print(f"Stereo reprojection error: {stereo_ret:.4f}")
    print(f"Baseline estimate:         {float(np.linalg.norm(translation)):.4f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

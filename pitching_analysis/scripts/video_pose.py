#!/usr/bin/env python3
"""
video_pose.py — 投球動画を MediaPipe Pose で解析し、関節角の時系列CSVと
骨格を重ねた注釈動画を出力する。

できること（2D・単一カメラ）:
    - 骨盤-肩の分離角（rear/face視点向け）   … H-B
    - 踏み出し脚の膝角（伸展=ブロック）        … H-H
    - 体幹の前傾/側屈                          … H-B/H-D
    - 腕スロット（肘の肩に対する高さ）          … H-D
    - 各指標の時系列CSV ＋ 極値サマリー（最大分離角・最小膝角 等）

使い方:
    python3 video_pose.py input.mp4 --hand right --view rear -o ./out_video
        --hand : right / left（投球腕。踏み出し脚＝反対側を自動選択）
        --view : side / rear / face（指標の解釈ヒント。計算自体は共通）

依存: mediapipe, opencv-python, numpy
    pip install mediapipe opencv-python numpy

注意:
    1台のスマホ=2D解析。面外（カメラに対し奥行き方向）の動きには誤差が出る。
    分離角は rear/face、ブロック/前傾は side が読みやすい。同じ画角で撮ると比較可。
    高フレームレート（120/240fps）推奨。
"""
import argparse
import csv
import math
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
    import mediapipe as mp
except ImportError as e:
    sys.exit(f"依存が必要です: pip install mediapipe opencv-python numpy （{e}）")

# mediapipe は 0.10.x 後半で従来の solutions API を廃し Tasks API へ移行。
# どちらでも動くよう両対応する。
HAS_SOLUTIONS = hasattr(mp, "solutions")

# MediaPipe Pose ランドマーク index
L_SH, R_SH = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANK, R_ANK = 27, 28
L_ELB, R_ELB = 13, 14

# 骨格描画用の主要セグメント（Tasks API 時の手動描画に使用）
_EDGES = [(L_SH, R_SH), (L_HIP, R_HIP), (L_SH, L_HIP), (R_SH, R_HIP),
          (L_HIP, L_KNEE), (L_KNEE, L_ANK), (R_HIP, R_KNEE), (R_KNEE, R_ANK),
          (L_SH, L_ELB), (L_ELB, 15), (R_SH, R_ELB), (R_ELB, 16)]

_TASKS_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/"
                    "pose_landmarker/pose_landmarker_full/float16/latest/"
                    "pose_landmarker_full.task")


def _ensure_model():
    """Tasks API 用モデルをカレント/スクリプト隣に用意（無ければDL）。"""
    import urllib.request
    for cand in (Path("pose_landmarker.task"),
                 Path(__file__).parent / "pose_landmarker.task"):
        if cand.exists():
            return str(cand)
    dst = Path("pose_landmarker.task")
    print(f"[dl] モデル取得中: {_TASKS_MODEL_URL}")
    urllib.request.urlretrieve(_TASKS_MODEL_URL, dst)
    return str(dst)


class PoseBackend:
    """solutions / tasks のどちらでも、フレーム→正規化ランドマーク列を返す。"""

    def __init__(self, fps):
        self.fps = fps
        self.api = "solutions" if HAS_SOLUTIONS else "tasks"
        if self.api == "solutions":
            self._pose = mp.solutions.pose.Pose(
                model_complexity=1, min_detection_confidence=0.5,
                min_tracking_confidence=0.5)
        else:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            base = python.BaseOptions(model_asset_path=_ensure_model())
            opts = vision.PoseLandmarkerOptions(
                base_options=base, running_mode=vision.RunningMode.VIDEO,
                num_poses=1)
            self._pose = vision.PoseLandmarker.create_from_options(opts)

    def landmarks(self, frame_bgr, frame_idx):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        if self.api == "solutions":
            res = self._pose.process(rgb)
            return res.pose_landmarks.landmark if res.pose_landmarks else None
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self._pose.detect_for_video(img, int(frame_idx / self.fps * 1000))
        return res.pose_landmarks[0] if res.pose_landmarks else None


def draw_skeleton(frame, lm, w, h):
    """ランドマークと主要セグメントを描く（両API共通の手動描画）。"""
    for p in lm:
        cv2.circle(frame, (int(p.x * w), int(p.y * h)), 3, (0, 200, 255), -1)
    for a, b in _EDGES:
        pa = (int(lm[a].x * w), int(lm[a].y * h))
        pb = (int(lm[b].x * w), int(lm[b].y * h))
        cv2.line(frame, pa, pb, (0, 255, 0), 2)


def reencode_h264(src_mp4, slowmo=0.0):
    """ffmpeg があれば annotated.mp4 を H.264(yuv420p) に再エンコードし、
    多くのプレーヤー/ブラウザで再生可能にする。OpenCV の mp4v は非互換な
    ことが多いため。slowmo>1 で低速版(annotated_slow.mp4)も作る。
    ffmpeg が無ければ mp4v のまま残し、警告を出すだけ。"""
    import shutil
    import subprocess
    src_mp4 = Path(src_mp4)
    if shutil.which("ffmpeg") is None:
        print("[warn] ffmpeg未検出: annotated.mp4 は mp4v のまま。"
              "再生できない場合は H.264 へ変換してください。")
        return
    tmp = src_mp4.with_name("_h264.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", str(src_mp4), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    tmp.replace(src_mp4)
    print(f"[ok] H.264へ再エンコード: {src_mp4}")
    if slowmo and slowmo > 1.0:
        slow = src_mp4.with_name("annotated_slow.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", str(src_mp4), "-filter:v",
                        f"setpts={slowmo}*PTS", "-r", "30", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                        str(slow)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True)
        print(f"[ok] スロー版({slowmo}倍遅): {slow}")


def angle_of_line(p1, p2):
    """2点を結ぶ線の画像平面上の角度(度)。"""
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def joint_angle(a, b, c):
    """点b を頂点とする ∠abc（度, 0-180）。"""
    ba = np.array([a[0] - b[0], a[1] - b[1]])
    bc = np.array([c[0] - b[0], c[1] - b[1]])
    nba, nbc = np.linalg.norm(ba), np.linalg.norm(bc)
    if nba == 0 or nbc == 0:
        return None
    cosv = np.clip(np.dot(ba, bc) / (nba * nbc), -1.0, 1.0)
    return math.degrees(math.acos(cosv))


def trunk_tilt(hip_mid, sh_mid):
    """体幹ベクトル(腰中央→肩中央)の鉛直からの傾き(度)。0=直立。"""
    v = np.array([sh_mid[0] - hip_mid[0], sh_mid[1] - hip_mid[1]])
    if np.linalg.norm(v) == 0:
        return None
    # 画像座標はy下向き。鉛直上=(0,-1)
    vertical = np.array([0, -1])
    cosv = np.clip(np.dot(v, vertical) / np.linalg.norm(v), -1.0, 1.0)
    return math.degrees(math.acos(cosv))


def compute_metrics(lm, w, h, hand):
    """1フレームのランドマークから指標を計算。lm は normalized landmarks。"""
    def pt(i):
        return (lm[i].x * w, lm[i].y * h)

    sh_line = angle_of_line(pt(L_SH), pt(R_SH))
    hip_line = angle_of_line(pt(L_HIP), pt(R_HIP))
    separation = abs(sh_line - hip_line)
    if separation > 180:
        separation = 360 - separation

    # 踏み出し脚 = 投球腕の反対側
    if hand == "right":
        knee = joint_angle(pt(L_HIP), pt(L_KNEE), pt(L_ANK))
        elb_y, sh_y = pt(R_ELB)[1], pt(R_SH)[1]
    else:
        knee = joint_angle(pt(R_HIP), pt(R_KNEE), pt(R_ANK))
        elb_y, sh_y = pt(L_ELB)[1], pt(L_SH)[1]

    hip_mid = ((pt(L_HIP)[0] + pt(R_HIP)[0]) / 2, (pt(L_HIP)[1] + pt(R_HIP)[1]) / 2)
    sh_mid = ((pt(L_SH)[0] + pt(R_SH)[0]) / 2, (pt(L_SH)[1] + pt(R_SH)[1]) / 2)
    tilt = trunk_tilt(hip_mid, sh_mid)

    # 肘が肩より上か（負=肘が高い, 画像y下向き）。腕スロットの目安
    arm_slot = sh_y - elb_y

    return {
        "separation_deg": round(separation, 1),
        "lead_knee_deg": round(knee, 1) if knee is not None else "",
        "trunk_tilt_deg": round(tilt, 1) if tilt is not None else "",
        "arm_slot_px": round(arm_slot, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="入力動画 (mp4 等)")
    ap.add_argument("--hand", choices=["right", "left"], default="right",
                    help="投球腕（踏み出し脚は反対側）")
    ap.add_argument("--view", choices=["side", "rear", "face"], default="rear",
                    help="撮影視点（解釈ヒント）")
    ap.add_argument("-o", "--out", default="./out_video", help="出力先")
    ap.add_argument("--slowmo", type=float, default=3.0,
                    help="スロー版の倍率(例3=1/3速)。0で無効。ffmpeg必須")
    args = ap.parse_args()

    src = Path(args.video)
    if not src.exists():
        sys.exit(f"動画が見つかりません: {src}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        sys.exit(f"動画を開けません: {src}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        str(out / "annotated.mp4"),
        cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    backend = PoseBackend(fps)
    print(f"[info] mediapipe API: {backend.api}")
    rows = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        lm = backend.landmarks(frame, frame_idx)
        if lm is not None:
            m = compute_metrics(lm, w, h, args.hand)
            m["frame"] = frame_idx
            m["t_sec"] = round(frame_idx / fps, 3)
            rows.append(m)
            draw_skeleton(frame, lm, w, h)
            y = 30
            for k in ("separation_deg", "lead_knee_deg", "trunk_tilt_deg"):
                cv2.putText(frame, f"{k}: {m[k]}", (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                y += 28
        writer.write(frame)
        frame_idx += 1
    cap.release()
    writer.release()
    reencode_h264(out / "annotated.mp4", slowmo=args.slowmo)

    if not rows:
        sys.exit("姿勢を検出できませんでした（明るさ・全身が写るか・画角を確認）")

    cols = ["frame", "t_sec", "separation_deg", "lead_knee_deg",
            "trunk_tilt_deg", "arm_slot_px"]
    with (out / "pose_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=cols)
        wcsv.writeheader()
        wcsv.writerows(rows)

    # 極値サマリー
    def best(key, fn):
        vals = [(r[key], r["t_sec"]) for r in rows if isinstance(r[key], (int, float))]
        return fn(vals, default=(None, None)) if vals else (None, None)

    max_sep = best("separation_deg", lambda v, default: max(v, default=default))
    min_knee = best("lead_knee_deg", lambda v, default: min(v, default=default))
    print(f"[ok] {len(rows)}フレーム解析 -> {out}/annotated.mp4, pose_metrics.csv")
    print("==== 極値サマリー ====")
    print(f"最大 骨盤-肩 分離角: {max_sep[0]}° (t={max_sep[1]}s)  ※接地付近で確認(H-B)")
    print(f"踏み出し脚 最小膝角: {min_knee[0]}°  ※リリースで伸展(180寄り)か(H-H)")
    print("=====================")
    print("注: 2D解析の近似値。同一画角での相対変化・トレンドで判断を。")


if __name__ == "__main__":
    main()

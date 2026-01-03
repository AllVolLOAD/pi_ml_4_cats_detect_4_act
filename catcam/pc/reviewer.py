import argparse
import glob
import json
import os
import time

import cv2
import yaml


CAT_MAP = {
    "1": "cat_1",
    "2": "cat_2",
    "3": "cat_3",
    "4": "cat_4",
}

ACTIVITY_MAP = {
    "1": "eating",
    "2": "drinking",
    "3": "playing",
    "4": "grooming",
    "5": "sleeping",
}


def load_queue_meta(queue_path: str) -> dict:
    if not os.path.exists(queue_path):
        return {}
    meta = {}
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                meta[entry.get("clip_id")] = entry
            except json.JSONDecodeError:
                continue
    return meta


def load_labeled_ids(labels_path: str) -> set:
    if not os.path.exists(labels_path):
        return set()
    ids = set()
    with open(labels_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                clip_id = entry.get("clip_id")
                if clip_id:
                    ids.add(clip_id)
            except json.JSONDecodeError:
                continue
    return ids


def play_clip(path: str) -> bool:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"Cannot open clip: {path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25.0
    delay = max(1, int(1000 / fps))

    cv2.namedWindow("review", cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("review", frame)
        key = cv2.waitKey(delay) & 0xFF
        if key == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return False

    cap.release()
    cv2.waitKey(1)
    return True


def main():
    parser = argparse.ArgumentParser(description="Review queue")
    parser.add_argument("--config", type=str, default="config.yaml")
    parser.add_argument("--queue-dir", type=str, default=None)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    queue_dir = args.queue_dir or config.get("review", {}).get("queue_dir", "../data/review_queue")
    if not os.path.isabs(queue_dir):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        queue_dir = os.path.abspath(os.path.join(base_dir, queue_dir))

    os.makedirs(queue_dir, exist_ok=True)

    queue_path = os.path.join(queue_dir, "queue.jsonl")
    labels_path = os.path.join(queue_dir, "labels.jsonl")

    meta = load_queue_meta(queue_path)
    labeled = load_labeled_ids(labels_path)

    clips = sorted(glob.glob(os.path.join(queue_dir, "*.mp4")))
    if not clips:
        print("No clips in queue")
        return

    for clip in clips:
        clip_id = os.path.splitext(os.path.basename(clip))[0]
        if clip_id in labeled:
            continue

        entry = meta.get(clip_id, {})
        pred_activity = entry.get("pred_activity", "")
        pred_conf = entry.get("pred_conf", 0.0)
        print(f"Clip: {clip_id} | pred={pred_activity} conf={pred_conf:.2f}")

        if not play_clip(clip):
            print("Quit")
            return

        while True:
            cat = input("Cat [1-4], s=skip, q=quit: ").strip().lower()
            if cat in ("q", "quit"):
                return
            if cat in ("s", "skip"):
                break
            if cat not in CAT_MAP:
                continue

            act = input("Activity [1-5]: ").strip()
            if act not in ACTIVITY_MAP:
                continue

            label = {
                "clip_id": clip_id,
                "clip_path": clip,
                "cat_id": CAT_MAP[cat],
                "activity": ACTIVITY_MAP[act],
                "ts": time.time(),
                "pred_activity": pred_activity,
                "pred_conf": pred_conf,
                "source_video": entry.get("source_video"),
                "start_ts_sec": entry.get("start_ts_sec"),
                "duration_sec": entry.get("duration_sec"),
            }

            with open(labels_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(label, ensure_ascii=False) + "\n")
            labeled.add(clip_id)
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

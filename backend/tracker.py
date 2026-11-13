"""
ROADVISION AI - Video Inspection and Persistent Multi-Object Tracking Engine
Implements frame-by-frame inference, ByteTrack-inspired Centroid & IoU association,
persistent unique defect tracking, and memory-optimized video generation.
"""
import os
import cv2
import numpy as np
from collections import deque
from backend.detector import detector, compute_dhash

class TrackedDefect:
    def __init__(self, track_id, category_code, class_name, display_name, bbox, conf, frame_idx, time_sec):
        self.track_id = track_id
        self.category_code = category_code
        self.class_name = class_name
        self.display_name = display_name
        self.bbox = bbox # [x1, y1, x2, y2]
        self.max_conf = conf
        self.conf_history = [conf]
        self.first_frame = frame_idx
        self.last_frame = frame_idx
        self.first_time = time_sec
        self.last_time = time_sec
        self.missed_frames = 0
        self.detection_count = 1
        self.trajectory = deque(maxlen=30)
        self.trajectory.append(self.get_center())
        self.image_hash = None
        self.severity = "Minor"

    def get_center(self):
        return int((self.bbox[0] + self.bbox[2]) / 2), int((self.bbox[1] + self.bbox[3]) / 2)

    def update(self, bbox, conf, frame_idx, time_sec):
        self.bbox = bbox
        self.conf_history.append(conf)
        self.max_conf = max(self.max_conf, conf)
        self.last_frame = frame_idx
        self.last_time = time_sec
        self.missed_frames = 0
        self.detection_count += 1
        self.trajectory.append(self.get_center())

def compute_box_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    unionArea = areaA + areaB - interArea
    if unionArea <= 0:
        return 0.0
    return interArea / unionArea


def _draw_track_overlay(frame, track):
    """Draws a visible bounding box and compact track label onto a video frame."""
    height, width = frame.shape[:2]
    x1 = max(0, min(width - 1, int(track.bbox[0])))
    y1 = max(0, min(height - 1, int(track.bbox[1])))
    x2 = max(0, min(width - 1, int(track.bbox[2])))
    y2 = max(0, min(height - 1, int(track.bbox[3])))
    if x2 <= x1 or y2 <= y1:
        return

    color = (0, 255, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    label = f"ID: {track.track_id} ({track.severity})"
    cv2.putText(
        frame,
        label,
        (x1, max(15, y1 - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        color,
        1,
        cv2.LINE_AA
    )


class VideoDamageTracker:
    def __init__(self, max_missed=20, iou_threshold=0.25, center_dist_thresh=85.0):
        self.max_missed = max_missed
        self.iou_threshold = iou_threshold
        self.center_dist_thresh = center_dist_thresh
        self.active_tracks = []
        self.completed_tracks = []
        self.category_counters = {"D00": 1, "D10": 1, "D20": 1, "D40": 1}

    def _generate_track_id(self, cat_code):
        num = self.category_counters.get(cat_code, 1)
        self.category_counters[cat_code] = num + 1
        prefix = "POTHOLE" if cat_code == "D40" else ("CRACK" if cat_code in ["D00", "D10"] else "FATIGUE")
        return f"{prefix}-{num:03d}"

    def update_frame(self, detections, frame_idx, time_sec):
        """
        Associates frame detections with existing tracks using bipartite IoU & Centroid matching.
        """
        matched_tracks = set()
        matched_dets = set()

        # Step 1: Match with active tracks based on category & IoU
        for d_idx, det in enumerate(detections):
            best_iou = 0.0
            best_track_idx = -1
            det_bbox = det["bbox"]
            det_center = ((det_bbox[0] + det_bbox[2]) // 2, (det_bbox[1] + det_bbox[3]) // 2)

            for t_idx, track in enumerate(self.active_tracks):
                if t_idx in matched_tracks:
                    continue
                # Same general damage type check
                if track.category_code == det["category_code"]:
                    iou = compute_box_iou(track.bbox, det_bbox)
                    tr_center = track.get_center()
                    dist = np.hypot(tr_center[0] - det_center[0], tr_center[1] - det_center[1])

                    # Match if high IoU or reasonable center proximity
                    if iou > best_iou and (iou >= self.iou_threshold or dist <= self.center_dist_thresh):
                        best_iou = iou
                        best_track_idx = t_idx

            if best_track_idx != -1:
                track = self.active_tracks[best_track_idx]
                track.update(det["bbox"], det["confidence"], frame_idx, time_sec)
                track.severity = det["severity"]
                matched_tracks.add(best_track_idx)
                matched_dets.add(d_idx)
                det["track_id"] = track.track_id
            else:
                # Will spawn new track below
                pass

        # Step 2: Increment missed frames for unmatched active tracks
        unmatched_active = []
        for t_idx, track in enumerate(self.active_tracks):
            if t_idx not in matched_tracks:
                track.missed_frames += 1
                if track.missed_frames > self.max_missed:
                    self.completed_tracks.append(track)
                else:
                    unmatched_active.append(track)
            else:
                unmatched_active.append(track)

        self.active_tracks = unmatched_active

        # Step 3: Initialize new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_dets:
                cat_code = det["category_code"]
                new_id = self._generate_track_id(cat_code)
                new_track = TrackedDefect(
                    track_id=new_id,
                    category_code=cat_code,
                    class_name=det["class_name"],
                    display_name=det["display_name"],
                    bbox=det["bbox"],
                    conf=det["confidence"],
                    frame_idx=frame_idx,
                    time_sec=time_sec
                )
                new_track.severity = det["severity"]
                new_track.image_hash = det.get("image_hash")
                self.active_tracks.append(new_track)
                det["track_id"] = new_id

    def finalize(self):
        self.completed_tracks.extend(self.active_tracks)
        self.active_tracks = []
        return self.completed_tracks

def process_video_inspection(
    video_path,
    output_video_path,
    conf_thresh=0.15,
    iou_thresh=0.45,
    sample_stride=2,
    imgsz=640,
    progress_callback=None
):
    """
    Processes video media, runs model inference, maintains persistent tracking,
    renders annotated video, and returns comprehensive unique defect analytics.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0.0

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(output_video_path, fourcc, fps / sample_stride, (width, height))

    tracker = VideoDamageTracker()
    frame_idx = 0
    saved_frames = 0
    total_frame_detections = 0
    frame_log = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if frame_idx % sample_stride != 0:
                continue

            time_sec = round(frame_idx / fps, 2)

            # Run detector directly on in-memory frame using high-recall multi-model ensemble
            annotated_frame, frame_dets, _ = detector.detect_image(
                source=frame,
                conf_thresh=conf_thresh,
                iou_thresh=iou_thresh,
                model_choice="ensemble",
                imgsz=imgsz
            )

            total_frame_detections += len(frame_dets)

            # Update multi-object tracker
            tracker.update_frame(frame_dets, frame_idx, time_sec)

            # Render overlay: Persistent Track ID and trajectories on annotated frame
            for track in tracker.active_tracks:
                pts = list(track.trajectory)
                for i in range(1, len(pts)):
                    cv2.line(annotated_frame, pts[i - 1], pts[i], (0, 255, 255), 2)

                _draw_track_overlay(annotated_frame, track)

            # Render global HUD on video
            cv2.rectangle(annotated_frame, (10, 10), (380, 80), (0, 0, 0), -1)
            cv2.putText(
                annotated_frame,
                f"ROADVISION AI | Frame: {frame_idx}/{total_frames}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1
            )
            cv2.putText(
                annotated_frame,
                f"Active Tracks: {len(tracker.active_tracks)} | Unique Defects: {len(tracker.active_tracks) + len(tracker.completed_tracks)}",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                1
            )

            out_writer.write(annotated_frame)
            saved_frames += 1

            if frame_dets:
                frame_log.append({
                    "frame": frame_idx,
                    "time_sec": time_sec,
                    "detections_count": len(frame_dets),
                    "defects": frame_dets
                })

            if progress_callback and total_frames > 0:
                progress_callback(frame_idx / total_frames)

    finally:
        cap.release()
        out_writer.release()

        # Convert output video to web-standard H.264 (AVC1) so all HTML5 browsers play it instantly
        temp_raw_path = output_video_path + ".raw.mp4"
        try:
            import imageio_ffmpeg
            import subprocess
            if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                os.replace(output_video_path, temp_raw_path)
                cmd = [
                    imageio_ffmpeg.get_ffmpeg_exe(), "-y",
                    "-i", temp_raw_path,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    output_video_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(temp_raw_path):
                    os.remove(temp_raw_path)
        except Exception as conv_err:
            print(f"[Tracker] H.264 browser conversion note: {conv_err}")
            if os.path.exists(temp_raw_path) and not os.path.exists(output_video_path):
                os.replace(temp_raw_path, output_video_path)

    all_tracks = tracker.finalize()

    # Aggregate unique defect counts by category & severity
    unique_summary = {
        "D00": 0, "D10": 0, "D20": 0, "D40": 0,
        "Minor": 0, "Moderate": 0, "Severe": 0
    }
    unique_defect_list = []
    for tr in all_tracks:
        unique_summary[tr.category_code] = unique_summary.get(tr.category_code, 0) + 1
        unique_summary[tr.severity] = unique_summary.get(tr.severity, 0) + 1
        unique_defect_list.append({
            "track_id": tr.track_id,
            "category_code": tr.category_code,
            "display_name": tr.display_name,
            "severity": tr.severity,
            "first_frame": tr.first_frame,
            "last_frame": tr.last_frame,
            "duration_frames": tr.last_frame - tr.first_frame + 1,
            "detection_count": tr.detection_count,
            "avg_confidence": round(float(np.mean(tr.conf_history)), 3),
            "max_confidence": round(float(tr.max_conf), 3),
            "final_bbox": tr.bbox
        })

    # Duplicates removed calculation
    duplicates_removed = max(0, total_frame_detections - len(all_tracks))

    # Severity Mix (Critical, High, Medium, Low)
    severity_mix = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0
    }
    for tr in all_tracks:
        if tr.severity == "Severe" or (tr.category_code == "D40" and tr.max_conf >= 0.70):
            severity_mix["Critical"] += 1
        elif tr.severity == "Moderate" or tr.category_code in ["D40", "D20"]:
            severity_mix["High"] += 1
        elif tr.category_code in ["D00", "D10"]:
            severity_mix["Medium"] += 1
        else:
            severity_mix["Low"] += 1

    # Damage timeline aggregation across video seconds
    damage_timeline = []
    if duration_sec > 0:
        time_step = max(1.0, round(duration_sec / 20.0, 1))
        curr_t = 0.0
        while curr_t <= duration_sec + 0.1:
            cnt = sum(1 for tr in all_tracks if tr.first_time <= curr_t <= tr.last_time + 0.5)
            damage_timeline.append({
                "time_sec": round(curr_t, 1),
                "timestamp_str": f"{int(curr_t//60):02d}:{int(curr_t%60):02d}",
                "damage_count": cnt
            })
            curr_t += time_step

    return {
        "total_frames": total_frames,
        "processed_frames": saved_frames,
        "fps": fps,
        "duration_sec": round(duration_sec, 2),
        "clip_length_sec": round(duration_sec, 2),
        "total_frame_detections": total_frame_detections,
        "raw_boxes_count": total_frame_detections,
        "unique_defects_count": len(all_tracks),
        "unique_damages": len(all_tracks),
        "duplicates_removed": duplicates_removed,
        "severity_mix": severity_mix,
        "damage_timeline": damage_timeline,
        "unique_summary": unique_summary,
        "tracked_defects": unique_defect_list,
        "unique_damages_list": unique_defect_list,
        "frame_log": frame_log
    }

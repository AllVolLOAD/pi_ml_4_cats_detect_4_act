"""
Инструмент разметки: ручная аннотация bbox и классов активности
"""

import cv2
import json
import yaml
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np


class Annotator:
    def __init__(self, video_path: str, output_path: str):
        self.video_path = video_path
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.annotations = []
        self.current_frame = 0
        self.drawing = False
        self.start_point = None
        self.current_box = None
        self.selected_class = "eating"  # eating, drinking, playing, sleeping
        
        self.classes = ["eating", "drinking", "playing", "sleeping"]
        self.class_colors = {
            "eating": (0, 255, 0),
            "drinking": (255, 0, 0),
            "playing": (0, 165, 255),
            "sleeping": (128, 0, 128)
        }
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.current_box = (self.start_point, (x, y))
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            if self.start_point:
                x1, y1 = self.start_point
                x2, y2 = x, y
                box = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
                self.annotations.append({
                    "frame": self.current_frame,
                    "bbox": box,
                    "class": self.selected_class,
                    "timestamp": self.current_frame / self.fps
                })
                self.current_box = None
    
    def run(self):
        cv2.namedWindow("Annotator")
        cv2.setMouseCallback("Annotator", self.mouse_callback)
        
        print("Управление:")
        print("  Мышь: рисуем bbox")
        print("  1-4: выбор класса (eating/drinking/playing/sleeping)")
        print("  Space: следующее видео")
        print("  S: сохранить")
        print("  Q: выход")
        
        while True:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if not ret:
                break
            
            display_frame = frame.copy()
            
            # Рисуем текущий bbox
            if self.current_box:
                pt1, pt2 = self.current_box
                cv2.rectangle(display_frame, pt1, pt2, self.class_colors[self.selected_class], 2)
            
            # Рисуем существующие аннотации
            for ann in self.annotations:
                if ann["frame"] == self.current_frame:
                    x1, y1, x2, y2 = ann["bbox"]
                    color = self.class_colors[ann["class"]]
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(display_frame, ann["class"], (x1, y1-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Инфо
            info = f"Frame: {self.current_frame}/{self.total_frames} | Class: {self.selected_class} | Annotations: {len(self.annotations)}"
            cv2.putText(display_frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("Annotator", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                self.current_frame = min(self.current_frame + int(self.fps), self.total_frames - 1)
            elif key == ord('s'):
                self.save()
            elif key == ord('1'):
                self.selected_class = "eating"
            elif key == ord('2'):
                self.selected_class = "drinking"
            elif key == ord('3'):
                self.selected_class = "playing"
            elif key == ord('4'):
                self.selected_class = "sleeping"
            elif key == 81:  # Left arrow
                self.current_frame = max(0, self.current_frame - int(self.fps))
            elif key == 83:  # Right arrow
                self.current_frame = min(self.current_frame + int(self.fps), self.total_frames - 1)
        
        cv2.destroyAllWindows()
        self.save()
    
    def save(self):
        data = {
            "video_path": self.video_path,
            "fps": self.fps,
            "total_frames": self.total_frames,
            "annotations": self.annotations
        }
        with open(self.output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Сохранено: {len(self.annotations)} аннотаций в {self.output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Использование: python annotator.py <video_path> <output_json>")
        sys.exit(1)
    
    annotator = Annotator(sys.argv[1], sys.argv[2])
    annotator.run()


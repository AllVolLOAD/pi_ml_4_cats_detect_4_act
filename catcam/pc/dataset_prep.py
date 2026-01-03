"""
Подготовка датасета: извлечение кадров, конвертация аннотаций в YOLO формат
"""

import json
import cv2
from pathlib import Path
from typing import List, Dict
import yaml


class DatasetPrep:
    def __init__(self, annotations_dir: str, videos_dir: str, output_dir: str):
        self.annotations_dir = Path(annotations_dir)
        self.videos_dir = Path(videos_dir)
        self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "labels").mkdir(exist_ok=True)
        
        self.class_map = {
            "eating": 0,
            "drinking": 1,
            "playing": 2,
            "sleeping": 3
        }
        
    def convert_to_yolo(self, bbox: List[int], img_width: int, img_height: int) -> List[float]:
        """Конвертация bbox [x1,y1,x2,y2] в YOLO формат [cx,cy,w,h] нормализованные"""
        x1, y1, x2, y2 = bbox
        cx = ((x1 + x2) / 2) / img_width
        cy = ((y1 + y2) / 2) / img_height
        w = (x2 - x1) / img_width
        h = (y2 - y1) / img_height
        return [cx, cy, w, h]
    
    def process_annotations(self):
        """Обработка всех аннотаций"""
        annotation_files = list(self.annotations_dir.glob("*.json"))
        
        train_images = []
        val_images = []
        
        for ann_file in annotation_files:
            print(f"Обработка {ann_file.name}...")
            
            with open(ann_file, 'r') as f:
                data = json.load(f)
            
            video_path = self.videos_dir / Path(data['video_path']).name
            if not video_path.exists():
                print(f"  Видео не найдено: {video_path}")
                continue
            
            cap = cv2.VideoCapture(str(video_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Группируем аннотации по кадрам
            frame_annotations = {}
            for ann in data['annotations']:
                frame = ann['frame']
                if frame not in frame_annotations:
                    frame_annotations[frame] = []
                frame_annotations[frame].append(ann)
            
            # Извлекаем кадры с аннотациями
            for frame_num, anns in frame_annotations.items():
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Сохраняем изображение
                img_filename = f"{ann_file.stem}_frame_{frame_num:06d}.jpg"
                img_path = self.output_dir / "images" / img_filename
                cv2.imwrite(str(img_path), frame)
                
                # Создаем YOLO label файл
                label_filename = img_filename.replace('.jpg', '.txt')
                label_path = self.output_dir / "labels" / label_filename
                
                with open(label_path, 'w') as f:
                    for ann in anns:
                        class_id = self.class_map[ann['class']]
                        yolo_bbox = self.convert_to_yolo(ann['bbox'], width, height)
                        f.write(f"{class_id} {' '.join(map(str, yolo_bbox))}\n")
                
                # Разделение train/val (80/20)
                import random
                if random.random() < 0.8:
                    train_images.append(str(img_path))
                else:
                    val_images.append(str(img_path))
            
            cap.release()
        
        # Сохраняем списки train/val
        with open(self.output_dir / "train.txt", 'w') as f:
            f.write('\n'.join(train_images))
        
        with open(self.output_dir / "val.txt", 'w') as f:
            f.write('\n'.join(val_images))
        
        # Создаем data.yaml для YOLOv8
        data_yaml = {
            "path": str(self.output_dir.absolute()),
            "train": "train.txt",
            "val": "val.txt",
            "nc": 4,
            "names": list(self.class_map.keys())
        }
        
        with open(self.output_dir / "data.yaml", 'w') as f:
            yaml.dump(data_yaml, f, default_flow_style=False)
        
        print(f"\nДатасет подготовлен:")
        print(f"  Train: {len(train_images)}")
        print(f"  Val: {len(val_images)}")
        print(f"  Output: {self.output_dir}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=str, default="../data/annotations")
    parser.add_argument("--videos", type=str, default="../data/raw_videos")
    parser.add_argument("--output", type=str, default="../data/dataset")
    args = parser.parse_args()
    
    prep = DatasetPrep(args.annotations, args.videos, args.output)
    prep.process_annotations()


"""
Telemetry logging for CatCam system
Logs telemetry data (CSV) and events (JSONL) for analysis
"""

import csv
import json
import os
from datetime import datetime
from typing import Optional, List, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import time

from roi.types import BBox, ActivityEvent
from roi.roi_engine import ROIResult


@dataclass
class FPSMetrics:
    """Трекинг FPS для различных компонентов"""
    receiver_fps: float = 0.0
    infer_fps: float = 0.0
    stream_fps: float = 0.0
    
    # Внутренние счетчики
    _receiver_frame_count: int = 0
    _infer_count: int = 0
    _stream_frame_count: int = 0
    _receiver_start_time: float = 0.0
    _infer_start_time: float = 0.0
    _stream_start_time: float = 0.0
    _update_interval: float = 1.0  # Обновлять FPS каждую секунду
    
    def update_receiver(self):
        """Вызывать при каждом кадре от receiver"""
        if self._receiver_start_time == 0.0:
            self._receiver_start_time = time.time()
            return
        
        self._receiver_frame_count += 1
        elapsed = time.time() - self._receiver_start_time
        if elapsed >= self._update_interval:
            self.receiver_fps = self._receiver_frame_count / elapsed
            self._receiver_frame_count = 0
            self._receiver_start_time = time.time()
    
    def update_infer(self):
        """Вызывать при каждом AI inference"""
        if self._infer_start_time == 0.0:
            self._infer_start_time = time.time()
            return
        
        self._infer_count += 1
        elapsed = time.time() - self._infer_start_time
        if elapsed >= self._update_interval:
            self.infer_fps = self._infer_count / elapsed
            self._infer_count = 0
            self._infer_start_time = time.time()
    
    def update_stream(self):
        """Вызывать при каждом кадре отправленном в streamer"""
        if self._stream_start_time == 0.0:
            self._stream_start_time = time.time()
            return
        
        self._stream_frame_count += 1
        elapsed = time.time() - self._stream_start_time
        if elapsed >= self._update_interval:
            self.stream_fps = self._stream_frame_count / elapsed
            self._stream_frame_count = 0
            self._stream_start_time = time.time()


class BBoxJitterTracker:
    """Трекинг jitter (смещение центра bbox)"""
    
    def __init__(self):
        self.last_center: Optional[Tuple[float, float]] = None
    
    def calculate_jitter(self, bbox: Optional[BBox]) -> float:
        """
        Вычисляет jitter (смещение центра относительно предыдущего кадра)
        Returns: расстояние в пикселях, или 0.0 если нет предыдущего центра
        """
        if bbox is None:
            self.last_center = None
            return 0.0
        
        current_center = bbox.center()
        
        if self.last_center is None:
            self.last_center = current_center
            return 0.0
        
        # Вычисляем расстояние между центрами
        dx = current_center[0] - self.last_center[0]
        dy = current_center[1] - self.last_center[1]
        jitter = (dx * dx + dy * dy) ** 0.5
        
        self.last_center = current_center
        return jitter


class TelemetryLogger:
    """Логирование телеметрии в CSV и событий в JSONL"""
    
    def __init__(self, log_dir: str = "logs", enabled: bool = True, flush_interval: float = 5.0):
        self.enabled = enabled
        self.log_dir = log_dir
        self.flush_interval = flush_interval
        self.last_flush_time = time.time()
        
        if not self.enabled:
            return
        
        # Создаем директорию для логов
        os.makedirs(log_dir, exist_ok=True)
        
        # Имя файла с датой
        date_str = datetime.now().strftime("%Y%m%d")
        telemetry_filename = f"telemetry_{date_str}.csv"
        events_filename = f"events_{date_str}.jsonl"
        
        self.telemetry_path = os.path.join(log_dir, telemetry_filename)
        self.events_path = os.path.join(log_dir, events_filename)
        
        # Открываем файлы
        self.telemetry_file = open(self.telemetry_path, 'a', newline='', encoding='utf-8')
        self.events_file = open(self.events_path, 'a', encoding='utf-8')
        
        # CSV writer для telemetry
        self.telemetry_writer = csv.writer(self.telemetry_file)
        
        # Записываем заголовок если файл новый
        if os.path.getsize(self.telemetry_path) == 0:
            header = [
                "ts", "has_bbox", "conf", "cx", "cy", "w", "h",
                "active_zone", "zone_timer_sec",
                "fps_receiver", "fps_infer", "fps_stream",
                "jitter_px"
            ]
            self.telemetry_writer.writerow(header)
            self.telemetry_file.flush()
        
        # Инициализируем трекеры
        self.fps_metrics = FPSMetrics()
        self.jitter_tracker = BBoxJitterTracker()
        
        print(f"[Telemetry] Логирование включено: {self.telemetry_path}, {self.events_path}")
    
    def log_telemetry(
        self,
        ts: float,
        bbox: Optional[BBox],
        conf: Optional[float],
        roi_result: Optional[ROIResult],
        fps_metrics: Optional[FPSMetrics] = None
    ):
        """Логирование телеметрии на каждом AI inference тике"""
        if not self.enabled:
            return
        
        # Используем переданный fps_metrics или внутренний
        if fps_metrics is None:
            fps_metrics = self.fps_metrics
        
        # Вычисляем jitter
        jitter_px = self.jitter_tracker.calculate_jitter(bbox)
        
        # Парсим данные
        has_bbox = 1 if bbox is not None else 0
        conf_value = conf if conf is not None else 0.0
        
        if bbox is not None:
            center = bbox.center()
            cx = center[0]
            cy = center[1]
            w = bbox.width()
            h = bbox.height()
        else:
            cx = cy = w = h = 0
        
        # ROI данные
        active_zone = roi_result.active_zone if roi_result else None
        zone_timer_sec = 0.0
        if roi_result and roi_result.active_zone:
            # Вычисляем таймер активности (нужно передавать из ROI Engine или хранить отдельно)
            # Пока что 0.0, можно добавить позже
            pass
        
        # Записываем строку
        row = [
            ts,
            has_bbox,
            f"{conf_value:.4f}",
            f"{cx:.2f}",
            f"{cy:.2f}",
            w,
            h,
            active_zone if active_zone else "",
            f"{zone_timer_sec:.2f}",
            f"{fps_metrics.receiver_fps:.2f}",
            f"{fps_metrics.infer_fps:.2f}",
            f"{fps_metrics.stream_fps:.2f}",
            f"{jitter_px:.2f}"
        ]
        
        self.telemetry_writer.writerow(row)
        
        # Flush периодически
        current_time = time.time()
        if current_time - self.last_flush_time >= self.flush_interval:
            self.telemetry_file.flush()
            self.events_file.flush()
            self.last_flush_time = current_time
    
    def log_event(self, event: ActivityEvent, avg_conf: Optional[float] = None):
        """Логирование события ROI"""
        if not self.enabled:
            return
        
        event_data = {
            "start_ts": event.start_ts,
            "end_ts": event.start_ts + event.duration_sec,
            "type": event.type,
            "duration": event.duration_sec,
            "avg_conf": avg_conf if avg_conf is not None else 0.0
        }
        
        json_line = json.dumps(event_data, ensure_ascii=False)
        self.events_file.write(json_line + "\n")
        
        # Flush сразу для событий (они важные)
        self.events_file.flush()
    
    def close(self):
        """Закрытие файлов"""
        if not self.enabled:
            return
        
        self.telemetry_file.flush()
        self.events_file.flush()
        self.telemetry_file.close()
        self.events_file.close()
        print("[Telemetry] Файлы закрыты")


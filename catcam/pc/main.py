"""
Главный скрипт для запуска всех компонентов CatCam системы
Интегрирует receiver, ai_detector и streamer в единый процесс
"""

import threading
import time
import signal
import sys
import yaml
import os
import glob
import cv2
import json
import shutil
from collections import deque
from typing import Optional
from receiver import SRTReceiver
from ai_detector import AIDetector
from streamer import Streamer
from roi import ROIEngine, ROIConfig, ZoneConfig, BBox, ROIResult
from telemetry import TelemetryLogger, FPSMetrics
from web_review import start_web_review_server
import subprocess


def load_roi_config(path: str = "config.yaml") -> ROIConfig:
    """Загрузка ROI конфигурации из YAML"""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    roi = cfg["roi"]
    zones = {}
    
    for name, z in roi["zones"].items():
        zones[name] = ZoneConfig(
            name=name,
            rect=tuple(z["rect"]),
            min_time_sec=float(z["min_time_sec"]),
            max_movement_px=float(z["max_movement_px"]) if "max_movement_px" in z else None,
        )
    
    priority = roi.get("priority", ["eating", "drinking", "sleeping", "playing"])
    hysteresis_ticks = roi.get("hysteresis_ticks", 3)
    
    return ROIConfig(
        frame_size=tuple(roi["frame_size"]),
        intersection_threshold=float(roi.get("intersection_threshold", 0.3)),
        zones=zones,
        priority=priority,
        hysteresis_ticks=int(hysteresis_ticks),
    )


def _resolve_path(base_dir: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(base_dir, path))


def _run_pull_once(sync_cfg: dict, base_dir: str):
    script_path = sync_cfg.get("script_path", "scripts/pull_from_pi.ps1")
    script_path = _resolve_path(base_dir, script_path)
    if not os.path.exists(script_path):
        print(f"[Sync] Script not found: {script_path}")
        return

    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
    pi_host = sync_cfg.get("pi_host")
    remote_dir = sync_cfg.get("remote_dir")
    local_dir = sync_cfg.get("local_dir")
    if pi_host:
        cmd += ["-PiHost", pi_host]
    if remote_dir:
        cmd += ["-RemoteDir", remote_dir]
    if local_dir:
        cmd += ["-LocalDir", _resolve_path(base_dir, local_dir)]

    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"[Sync] Pull failed: {e}")


def start_sync_thread(config: dict, config_path: str, base_dir: str, stop_event: threading.Event) -> Optional[threading.Thread]:
    sync_cfg = config.get("sync", {})
    if not sync_cfg.get("enabled", False):
        return None

    interval = float(sync_cfg.get("interval_sec", 120))

    def _loop():
        while not stop_event.is_set():
            _run_pull_once(sync_cfg, base_dir)
            run_backfill(config_path, config, base_dir)
            stop_event.wait(interval)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("[Sync] Started")
    return t


def start_pi_service(config: dict, base_dir: str) -> bool:
    """Запуск сервиса на Raspberry Pi через SSH"""
    pi_service_cfg = config.get("pi_service", {})
    if not pi_service_cfg.get("enabled", False):
        print("[PiService] Автозапуск сервиса на малине отключен в конфиге")
        return False
    
    script_path = pi_service_cfg.get("script_path", "scripts/start_pi_service.ps1")
    script_path = _resolve_path(base_dir, script_path)
    if not os.path.exists(script_path):
        print(f"[PiService] Script not found: {script_path}")
        return False
    
    pi_host = pi_service_cfg.get("pi_host", "mlprojectcat@192.168.1.103")
    service_name = pi_service_cfg.get("service_name", "cam-stream-record.service")
    
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path,
           "-PiHost", pi_host, "-ServiceName", service_name]
    
    try:
        print(f"[PiService] Запуск сервиса {service_name} на малине ({pi_host})...")
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("[PiService] Сервис на малине запущен успешно")
            # Даем время сервису запуститься
            print("[PiService] Ожидание запуска сервиса (3 сек)...")
            time.sleep(3)
            return True
        else:
            print(f"[PiService] Ошибка запуска сервиса (code={result.returncode})")
            if result.stdout:
                print(f"[PiService] stdout: {result.stdout}")
            if result.stderr:
                print(f"[PiService] stderr: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("[PiService] Таймаут при запуске сервиса (30 сек)")
        return False
    except Exception as e:
        print(f"[PiService] Исключение при запуске сервиса: {e}")
        return False




class ReviewClipper:
    def __init__(self, queue_dir: str, clip_sec: float, pre_roll_sec: float,
                 min_gap_sec: float, min_conf: float, max_clips: int):
        self.queue_dir = queue_dir
        self.clip_sec = clip_sec
        self.pre_roll_sec = pre_roll_sec
        self.min_gap_sec = min_gap_sec
        self.min_conf = min_conf
        self.max_clips = max_clips
        self.created = 0
        self.seq = 0
        self.last_clip_ts = -1.0
        self.active_writer = None
        self.frames_left = 0
        self.buffer = deque()
        self.buffer_max = 0
        self.clip_frames = 0
        self.source_video = ""
        self.queue_path = os.path.join(self.queue_dir, "queue.jsonl")
        os.makedirs(self.queue_dir, exist_ok=True)

    def set_video(self, source_video: str, fps: float):
        self.source_video = source_video
        fps = fps if fps and fps > 0 else 25.0
        self.clip_frames = max(1, int(self.clip_sec * fps))
        self.buffer_max = max(1, int(self.pre_roll_sec * fps))
        self.buffer = deque(maxlen=self.buffer_max)

    def push_frame(self, frame, video_ts: float):
        if self.buffer_max > 0:
            self.buffer.append(frame.copy())
        if self.active_writer is not None:
            self.active_writer.write(frame)
            self.frames_left -= 1
            if self.frames_left <= 0:
                self._close_writer()

    def on_detection(self, bbox: Optional[BBox], conf: Optional[float], video_ts: float,
                     pred_activity: Optional[str]):
        if self.active_writer is not None:
            return
        if self.created >= self.max_clips:
            return
        if conf is None or conf < self.min_conf:
            return
        if self.last_clip_ts >= 0 and (video_ts - self.last_clip_ts) < self.min_gap_sec:
            return

        clip_id = self._next_clip_id(video_ts)
        clip_path = os.path.join(self.queue_dir, f"{clip_id}.mp4")

        if not self.buffer:
            return

        h, w = self.buffer[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(clip_path, fourcc, max(1, self.clip_frames / self.clip_sec), (w, h))
        for frame in self.buffer:
            writer.write(frame)
        self.active_writer = writer
        self.frames_left = max(0, self.clip_frames - len(self.buffer))
        self.last_clip_ts = video_ts
        self.created += 1

        entry = {
            "clip_id": clip_id,
            "clip_path": clip_path,
            "source_video": self.source_video,
            "start_ts_sec": max(0.0, video_ts - self.pre_roll_sec),
            "duration_sec": self.clip_sec,
            "pred_activity": pred_activity or "",
            "pred_conf": float(conf) if conf is not None else 0.0,
            "bbox": [bbox.x1, bbox.y1, bbox.x2, bbox.y2] if bbox else None,
        }
        with open(self.queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _next_clip_id(self, video_ts: float) -> str:
        base = os.path.splitext(os.path.basename(self.source_video))[0]
        ts_ms = int(video_ts * 1000)
        clip_id = f"{base}_{ts_ms:010d}_{self.seq:04d}"
        self.seq += 1
        return clip_id

    def _close_writer(self):
        if self.active_writer is not None:
            self.active_writer.release()
            self.active_writer = None
            self.frames_left = 0

    def close(self):
        self._close_writer()


def _is_video_complete(path: str, min_size_bytes: int = 1024) -> bool:
    """Проверка, что видео файл завершен (не пишется)"""
    if not os.path.exists(path):
        return False
    
    # Проверяем минимальный размер
    size1 = os.path.getsize(path)
    if size1 < min_size_bytes:
        return False
    
    # Ждем немного и проверяем, изменился ли размер
    time.sleep(0.5)
    if not os.path.exists(path):
        return False
    
    size2 = os.path.getsize(path)
    # Если размер не изменился, файл вероятно завершен
    return size1 == size2


def _safe_move_file(src: str, dst: str, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """Безопасное перемещение файла с повторными попытками"""
    for attempt in range(max_retries):
        try:
            # Проверяем, что файл не заблокирован
            # Пытаемся открыть в режиме append - если файл заблокирован, это не сработает
            try:
                with open(src, 'r+b') as f:
                    pass
            except (PermissionError, IOError):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return False
            
            # Пытаемся переместить
            shutil.move(src, dst)
            return True
        except (PermissionError, IOError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"[Backfill] Archive move retry {attempt + 1}/{max_retries}: {src}")
                time.sleep(retry_delay)
            else:
                print(f"[Backfill] Archive move failed after {max_retries} attempts: {src} ({e})")
                return False
    return False


def _process_backfill_video(path: str, detector: AIDetector, roi_engine: Optional[ROIEngine],
                            telemetry: TelemetryLogger, fps_metrics: FPSMetrics,
                            ai_interval: float, frame_skip: int,
                            clipper: Optional[ReviewClipper]):
    # Проверяем, что файл завершен перед обработкой
    if not _is_video_complete(path):
        print(f"[Backfill] Skipping incomplete file: {path}")
        return
    
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"[Backfill] Cannot open: {path}")
        return

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if clipper:
            clipper.set_video(path, fps)

        last_ai_ts = -1.0
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            video_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

            if clipper:
                clipper.push_frame(frame, video_ts)

            run_detection = True
            if frame_skip > 1 and (frame_idx % frame_skip) != 0:
                run_detection = False

            if ai_interval > 0:
                if last_ai_ts >= 0 and (video_ts - last_ai_ts) < ai_interval:
                    run_detection = False

            if not run_detection:
                continue

            last_ai_ts = video_ts
            detections = detector.detect_all(frame)
            fps_metrics.update_infer()

            current_bbox = None
            conf = None
            roi_result = None

            if detections:
                if len(detections) > 1:
                    candidates = []
                    for bbox_list, conf_val in detections:
                        area = (bbox_list[2] - bbox_list[0]) * (bbox_list[3] - bbox_list[1])
                        candidates.append((bbox_list, conf_val, area))
                    best = max(candidates, key=lambda x: x[2])
                    bbox_list, conf = best[0], best[1]
                else:
                    bbox_list, conf = detections[0]

                current_bbox = BBox(x1=bbox_list[0], y1=bbox_list[1], x2=bbox_list[2], y2=bbox_list[3])

            if roi_engine:
                roi_result = roi_engine.update(current_bbox, video_ts)
                for ev in roi_result.events:
                    telemetry.log_event(ev, avg_conf=conf)

            telemetry.log_telemetry(
                ts=video_ts,
                bbox=current_bbox,
                conf=conf,
                roi_result=roi_result,
                fps_metrics=fps_metrics
            )

            if clipper and current_bbox is not None:
                pred_activity = roi_result.active_zone if roi_result else None
                clipper.on_detection(current_bbox, conf, video_ts, pred_activity)
    finally:
        # Гарантируем освобождение ресурсов
        cap.release()
        # Даем время системе освободить файл
        time.sleep(0.1)
    
    if clipper:
        clipper.close()


def run_backfill(config_path: str, config: dict, base_dir: str):
    backfill_cfg = config.get("backfill", {})
    enabled = backfill_cfg.get("enabled", False)
    if not enabled:
        print("[Backfill] Отключен в конфиге (enabled: false)")
        return

    input_dir = backfill_cfg.get("input_dir", "../data/raw_videos")
    input_dir = _resolve_path(base_dir, input_dir)
    if not os.path.exists(input_dir):
        return

    files = sorted(glob.glob(os.path.join(input_dir, "*.mp4")))
    if not files:
        return

    print(f"[Backfill] Processing {len(files)} file(s)")

    ai_interval = float(backfill_cfg.get("ai_interval_sec", 0))
    frame_skip = int(backfill_cfg.get("frame_skip", 1))
    delete_after = bool(backfill_cfg.get("delete_after", False))
    archive_dir = backfill_cfg.get("archive_dir")
    if archive_dir:
        archive_dir = _resolve_path(base_dir, archive_dir)
        os.makedirs(archive_dir, exist_ok=True)

    review_cfg = config.get("review", {})
    clipper = None
    if review_cfg.get("enabled", False):
        queue_dir = review_cfg.get("queue_dir", "../data/review_queue")
        queue_dir = _resolve_path(base_dir, queue_dir)
        clipper = ReviewClipper(
            queue_dir=queue_dir,
            clip_sec=float(review_cfg.get("clip_sec", 8)),
            pre_roll_sec=float(review_cfg.get("pre_roll_sec", 1)),
            min_gap_sec=float(review_cfg.get("min_gap_sec", 15)),
            min_conf=float(review_cfg.get("min_conf", 0.2)),
            max_clips=int(review_cfg.get("max_clips_per_run", 50))
        )

    detector = AIDetector(config_path, use_udp=False)

    roi_engine = None
    try:
        roi_config = load_roi_config(config_path)
        roi_engine = ROIEngine(roi_config)
    except Exception as e:
        print(f"[Backfill] ROI init failed: {e}")

    telemetry_cfg = config.get("telemetry", {})
    telemetry = TelemetryLogger(
        log_dir=telemetry_cfg.get("log_dir", "logs"),
        enabled=telemetry_cfg.get("enabled", True),
        flush_interval=telemetry_cfg.get("flush_interval", 5.0)
    )
    fps_metrics = FPSMetrics()

    for path in files:
        _process_backfill_video(path, detector, roi_engine, telemetry, fps_metrics, ai_interval, frame_skip, clipper)
        if delete_after:
            try:
                os.remove(path)
            except Exception as e:
                print(f"[Backfill] Delete failed: {path} ({e})")
        elif archive_dir:
            # Используем безопасное перемещение
            dest = os.path.join(archive_dir, os.path.basename(path))
            if not _safe_move_file(path, dest):
                print(f"[Backfill] Archive move failed after retries: {path}")

    detector.close()
    telemetry.close()
    print("[Backfill] Done")


class Watchdog:
    """Watchdog для мониторинга health компонентов и авто-рестарта"""
    
    def __init__(self, system, receiver_timeout_sec: float = 5.0, check_interval_sec: float = 2.0, auto_restart: bool = True):
        self.system = system
        self.receiver_timeout_sec = receiver_timeout_sec
        self.check_interval_sec = check_interval_sec
        self.auto_restart = auto_restart
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame_time: float = 0.0
        self.receiver_restart_time: float = 0.0  # Время последнего перезапуска receiver
        self.receiver_grace_period: float = 10.0  # Период ожидания после перезапуска (секунды)
    
    def update_frame_time(self):
        """Вызывать при получении каждого кадра"""
        self.last_frame_time = time.time()
    
    def check_receiver_health(self) -> bool:
        """Проверка health receiver: если нет кадров > timeout, возвращает False"""
        if self.system.receiver is None:
            return True  # Receiver не инициализирован - не проверяем
        
        # Если недавно перезапустили receiver, даем время на подключение
        current_time = time.time()
        if current_time - self.receiver_restart_time < self.receiver_grace_period:
            return True  # В grace period - не проверяем
        
        time_since_last_frame = current_time - self.last_frame_time
        
        if time_since_last_frame > self.receiver_timeout_sec:
            print(f"[Watchdog] Receiver не получает кадры {time_since_last_frame:.1f} сек (timeout: {self.receiver_timeout_sec} сек)")
            return False
        return True
    
    def check_streamer_health(self) -> bool:
        """Проверка health streamer: если FFmpeg процесс умер, возвращает False"""
        if self.system.streamer is None:
            return True  # Streamer не инициализирован - не проверяем
        
        # Проверяем только в режиме twitch (не preview)
        if self.system.streamer.mode != "twitch":
            return True  # В preview режиме нет FFmpeg процесса
        
        if self.system.streamer.ffmpeg_process is None:
            return True  # FFmpeg процесс еще не создан
        
        # Проверяем, жив ли процесс
        if self.system.streamer.ffmpeg_process.poll() is not None:
            print(f"[Watchdog] FFmpeg процесс умер (exit code: {self.system.streamer.ffmpeg_process.poll()})")
            return False
        
        return True
    
    def _watchdog_loop(self):
        """Основной цикл watchdog"""
        while self.running:
            try:
                # Проверка receiver
                if not self.check_receiver_health():
                    if self.auto_restart:
                        print("[Watchdog] Перезапуск receiver...")
                        try:
                            if self.system.receiver:
                                self.system.receiver.stop()
                            self.system.receiver = SRTReceiver(self.system.config_path)
                            if not self.system.receiver.start():
                                print("[Watchdog] Ошибка перезапуска receiver")
                            # Устанавливаем время перезапуска для grace period
                            self.receiver_restart_time = time.time()
                        except Exception as e:
                            print(f"[Watchdog] Исключение при перезапуске receiver: {e}")
                            self.receiver_restart_time = time.time()
                        # НЕ сбрасываем last_frame_time сразу - даем время на подключение
                
                # Проверка streamer
                if not self.check_streamer_health():
                    if self.auto_restart:
                        print("[Watchdog] Перезапуск streamer...")
                        try:
                            if self.system.streamer:
                                self.system.streamer.stop()
                            # Streamer перезапускается через start()
                            if self.system.streamer:
                                self.system.streamer.start()
                        except Exception as e:
                            print(f"[Watchdog] Исключение при перезапуске streamer: {e}")
                
            except Exception as e:
                print(f"[Watchdog] Ошибка в watchdog loop: {e}")
            
            time.sleep(self.check_interval_sec)
    
    def start(self):
        """Запуск watchdog в отдельном потоке"""
        if self.running:
            return
        
        self.running = True
        self.last_frame_time = time.time()
        self.thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.thread.start()
        print("[Watchdog] Запущен")
    
    def stop(self):
        """Остановка watchdog"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("[Watchdog] Остановлен")


class CatCamSystem:
    def __init__(self, config_path: str = "config.yaml"):
        """Инициализация полной системы"""
        self.config_path = config_path
        
        # Загружаем конфиг для телеметрии и streamer FPS
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        telemetry_config = config.get('telemetry', {})
        telemetry_enabled = telemetry_config.get('enabled', True)
        log_dir = telemetry_config.get('log_dir', 'logs')
        flush_interval = telemetry_config.get('flush_interval', 5.0)
        
        self.telemetry = TelemetryLogger(
            log_dir=log_dir,
            enabled=telemetry_enabled,
            flush_interval=flush_interval
        )
        self.fps_metrics = FPSMetrics()
        
        # Target FPS для streamer (из config)
        stream_config = config.get('stream', {})
        self.target_stream_fps = stream_config.get('fps', 25)
        self.last_stream_frame_time = 0.0
        
        # Watchdog конфигурация
        watchdog_config = config.get('watchdog', {})
        watchdog_enabled = watchdog_config.get('enabled', True)
        receiver_timeout_sec = watchdog_config.get('receiver_timeout_sec', 5.0)
        check_interval_sec = watchdog_config.get('streamer_check_interval_sec', 2.0)
        auto_restart = watchdog_config.get('auto_restart', True)
        
        # Логируем загруженные настройки watchdog для диагностики
        if watchdog_enabled:
            print(f"[Watchdog] Конфигурация: timeout={receiver_timeout_sec}с, check_interval={check_interval_sec}с, auto_restart={auto_restart}")
        
        self.watchdog: Optional[Watchdog] = None
        if watchdog_enabled:
            self.watchdog = Watchdog(
                self,
                receiver_timeout_sec=receiver_timeout_sec,
                check_interval_sec=check_interval_sec,
                auto_restart=auto_restart
            )
        
        self.receiver: Optional[SRTReceiver] = None
        self.ai_detector: Optional[AIDetector] = None
        self.streamer: Optional[Streamer] = None
        self.roi_engine: Optional[ROIEngine] = None
        self.running = False
    
    def start(self, use_ai: bool = True):
        """Запуск всех компонентов"""
        print("=" * 50)
        print("CatCam System - Запуск")
        print("=" * 50)
        
        # Инициализация компонентов
        self.receiver = SRTReceiver(self.config_path)
        self.streamer = Streamer(self.config_path, use_ai=use_ai)
        
        if use_ai:
            self.ai_detector = AIDetector(self.config_path, use_udp=True)
            
            # Загружаем ROI config один раз для ROI Engine и Streamer
            print("[2/4] Инициализация AI Detector...")
            # AI detector не требует явного start(), он работает в process_frame
            
            print("[3/4] Инициализация ROI Engine...")
            try:
                roi_config = load_roi_config(self.config_path)
                self.roi_engine = ROIEngine(roi_config)
                # Передаём ROI config в streamer для рисования зон
                self.streamer.roi_config = roi_config
                print("[ROI] ROI Engine инициализирован")
            except Exception as e:
                print(f"[ROI] Ошибка инициализации ROI Engine: {e}")
                print("[ROI] Продолжаем без ROI")
                self.roi_engine = None
        
        # Запуск компонентов
        print("\n[1/4] Запуск Receiver...")
        if not self.receiver.start():
            print("Ошибка: не удалось запустить Receiver")
            return False
        
        print("[4/4] Запуск Streamer...")
        self.streamer.start()
        
        # Запуск watchdog
        if self.watchdog:
            self.watchdog.start()
        
        self.running = True
        print("\nСистема запущена!")
        return True
    
    def run(self):
        """Основной цикл обработки"""
        if not self.running:
            return
        
        frame_count = 0
        last_fps_time = time.time()
        last_ai_time = time.time()
        ai_interval = 1.0 / 8.0  # AI обработка ~8 fps
        
        try:
            while self.running:
                # Получаем кадр от receiver
                result = self.receiver.get_frame(timeout=0.1)
                
                if result:
                    timestamp, frame = result
                    
                    # Обновляем watchdog (получен кадр)
                    if self.watchdog:
                        self.watchdog.update_frame_time()
                    
                    # Обновляем FPS метрики для receiver
                    self.fps_metrics.update_receiver()
                    
                    # Обработка через AI detector (если включен, ограничиваем частоту)
                    all_bboxes: list = []  # Все найденные коты для отрисовки
                    current_bbox: Optional[BBox] = None  # Один bbox для ROI Engine
                    conf: Optional[float] = None
                    all_detections = []
                    roi_result: Optional[ROIResult] = None
                    
                    if self.ai_detector:
                        current_time = time.time()
                        if current_time - last_ai_time >= ai_interval:
                            # Получаем всех котов
                            all_detections = self.ai_detector.detect_all(frame)
                            self.fps_metrics.update_infer()
                            last_ai_time = current_time
                            
                            if all_detections:
                                all_bboxes = all_detections
                                
                                # Для ROI выбираем самого крупного (для обратной совместимости)
                                if len(all_detections) > 1:
                                    # Сортируем по площади и берем самого крупного
                                    candidates = []
                                    for bbox_list, conf_val in all_detections:
                                        area = (bbox_list[2] - bbox_list[0]) * (bbox_list[3] - bbox_list[1])
                                        candidates.append((bbox_list, conf_val, area))
                                    best = max(candidates, key=lambda x: x[2])
                                    bbox_list, conf = best[0], best[1]
                                else:
                                    bbox_list, conf = all_detections[0]
                                
                                current_bbox = BBox(x1=bbox_list[0], y1=bbox_list[1], x2=bbox_list[2], y2=bbox_list[3])
                            
                            # Обработка через ROI Engine (использует одного кота - самого крупного)
                            if self.roi_engine:
                                current_ts = time.time()
                                roi_result = self.roi_engine.update(current_bbox, current_ts)
                                
                                # Логирование событий ROI
                                for ev in roi_result.events:
                                    print(f"[EVENT] {ev.type} {ev.duration_sec:.1f}s")
                                    # Логируем событие в телеметрию
                                    self.telemetry.log_event(ev, avg_conf=conf)
                            
                            # Логирование телеметрии (на каждом AI inference тике)
                            current_ts = time.time()
                            self.telemetry.log_telemetry(
                                ts=current_ts,
                                bbox=current_bbox,
                                conf=conf,
                                roi_result=roi_result,
                                fps_metrics=self.fps_metrics
                            )
                    
                    # Ограничение FPS для streamer (timestamp-based throttling)
                    current_time_for_stream = time.time()
                    frame_interval = 1.0 / self.target_stream_fps
                    
                    if current_time_for_stream - self.last_stream_frame_time >= frame_interval:
                        # Обновляем FPS метрики для streamer
                        self.fps_metrics.update_stream()
                        
                        # Отправка кадра в стрим
                        self.streamer.stream_frame(frame, all_bboxes=all_bboxes, roi_result=roi_result)
                        
                        self.last_stream_frame_time = current_time_for_stream
                    else:
                        # Пропускаем кадр для соблюдения target FPS
                        pass
                    
                    frame_count += 1
                    
                    # Выводим FPS каждые 5 секунд
                    current_time = time.time()
                    if current_time - last_fps_time >= 5.0:
                        fps = frame_count / (current_time - last_fps_time)
                        print(f"[System] FPS стрима: {fps:.1f} | Receiver: {self.fps_metrics.receiver_fps:.1f} | Infer: {self.fps_metrics.infer_fps:.1f}")
                        frame_count = 0
                        last_fps_time = current_time
                else:
                    # Нет кадров, небольшая задержка
                    time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nПолучен сигнал остановки...")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка всех компонентов"""
        print("\nОстановка системы...")
        self.running = False
        
        if self.receiver:
            self.receiver.stop()
        
        if self.streamer:
            self.streamer.stop()
        
        if self.ai_detector:
            self.ai_detector.close()
        
        if self.telemetry:
            self.telemetry.close()
        
        if self.watchdog:
            self.watchdog.stop()
        
        print("Система остановлена.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CatCam System - ?????? ???????')
    parser.add_argument('--no-ai', action='store_true', help='?????? ??? AI (?????? ????????????? ?????)')
    parser.add_argument('--config', type=str, default='config.yaml', help='???? ? config.yaml')
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Запуск сервиса на малине (если включено в конфиге)
    start_pi_service(config, base_dir)
    
    web_server = start_web_review_server(config, base_dir)
    sync_stop = threading.Event()
    sync_thread = start_sync_thread(config, args.config, base_dir, sync_stop)
    run_backfill(args.config, config, base_dir)

    system = CatCamSystem(config_path=args.config)
    
    # ????????? ???????? ??? ??????????? ??????????
    def signal_handler(sig, frame):
        sync_stop.set()
        if web_server:
            web_server.stop()
        if sync_thread:
            sync_thread.join(timeout=2.0)
        system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    use_ai = not args.no_ai
    
    if not system.start(use_ai=use_ai):
        sys.exit(1)
    
    system.run()
    sync_stop.set()
    if sync_thread:
        sync_thread.join(timeout=2.0)
    if web_server:
        web_server.stop()


if __name__ == "__main__":
    main()


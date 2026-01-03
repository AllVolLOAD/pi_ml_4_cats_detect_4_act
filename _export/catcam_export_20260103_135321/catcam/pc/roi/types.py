from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List

Rect = Tuple[int, int, int, int]  # x1, y1, x2, y2

@dataclass(frozen=True)
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    def as_rect(self) -> Rect:
        return (self.x1, self.y1, self.x2, self.y2)

    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    def area(self) -> int:
        return self.width() * self.height()

    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

@dataclass
class ZoneConfig:
    name: str
    rect: Rect
    min_time_sec: float
    max_movement_px: Optional[float] = None  # only for sleeping-like logic

@dataclass
class ROIConfig:
    frame_size: Tuple[int, int]  # (w, h)
    intersection_threshold: float
    zones: Dict[str, ZoneConfig]
    priority: List[str]  # e.g. ["eating", "drinking", "sleeping", "playing"]
    hysteresis_ticks: int = 3  # Зона меняется только после N тиков подряд

@dataclass
class ZoneState:
    active_since: Optional[float] = None
    accumulated_time: float = 0.0
    last_center: Optional[Tuple[float, float]] = None

@dataclass(frozen=True)
class ActivityEvent:
    type: str
    start_ts: float
    duration_sec: float


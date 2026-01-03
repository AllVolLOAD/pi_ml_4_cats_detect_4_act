from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

from .types import BBox, ROIConfig, ZoneState, ActivityEvent, Rect

def clamp_rect(r: Rect, w: int, h: int) -> Rect:
    x1, y1, x2, y2 = r
    x1 = max(0, min(x1, w))
    x2 = max(0, min(x2, w))
    y1 = max(0, min(y1, h))
    y2 = max(0, min(y2, h))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)

def intersection_area(a: Rect, b: Rect) -> int:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    return iw * ih

def ioa(bbox: BBox, roi: Rect) -> float:
    b_area = bbox.area()
    if b_area <= 0:
        return 0.0
    inter = intersection_area(bbox.as_rect(), roi)
    return inter / float(b_area)

def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5

@dataclass
class ROIResult:
    active_zone: Optional[str]
    active_ioa: float
    events: List[ActivityEvent]

class ROIEngine:
    """
    ROI-first activity engine.
    
    Input: bbox + timestamp (AI tick)
    Output: active zone + confirmed events
    """
    def __init__(self, cfg: ROIConfig):
        self.cfg = cfg
        self.states: Dict[str, ZoneState] = {name: ZoneState() for name in cfg.zones.keys()}
        w, h = cfg.frame_size
        
        # clamp zones once
        for z in cfg.zones.values():
            z.rect = clamp_rect(z.rect, w, h)  # type: ignore[attr-defined]
        
        self.current_activity: Optional[str] = None
        self.current_activity_start: Optional[float] = None
        
        # Hysteresis: зона меняется только после N тиков подряд
        self.candidate_zone: Optional[str] = None  # Новая зона-кандидат
        self.candidate_ticks: int = 0  # Счетчик тиков для кандидата

    def update(self, bbox: Optional[BBox], ts: float) -> ROIResult:
        """
        Call on every AI tick (5-10 fps), with a timestamp in seconds (time.time()).
        
        bbox can be None if cat not detected.
        """
        events: List[ActivityEvent] = []
        
        # If no bbox: reset all zone timers and maybe end current activity
        if bbox is None or bbox.area() == 0:
            self._reset_all(ts)
            if self.current_activity is not None and self.current_activity_start is not None:
                events.append(ActivityEvent(
                    self.current_activity,
                    self.current_activity_start,
                    ts - self.current_activity_start
                ))
            self.current_activity = None
            self.current_activity_start = None
            return ROIResult(active_zone=None, active_ioa=0.0, events=events)
        
        # Determine which zones are "active" by IoA threshold + special sleeping movement rule
        active_candidates: List[Tuple[str, float]] = []
        center = bbox.center()
        
        for name, zcfg in self.cfg.zones.items():
            s = self.states[name]
            z_ioa = ioa(bbox, zcfg.rect)
            is_geom_active = z_ioa >= self.cfg.intersection_threshold
            
            # sleeping rule: must be in zone + low movement
            if is_geom_active and zcfg.max_movement_px is not None:
                if s.last_center is None:
                    # first observation: don't instantly confirm sleeping, start tracking
                    pass
                else:
                    if dist(center, s.last_center) > zcfg.max_movement_px:
                        # movement too big -> treat as not active (and reset)
                        is_geom_active = False
            
            # Update last_center always (so sleeping can track movement)
            s.last_center = center
            
            # Update timers
            if is_geom_active:
                if s.active_since is None:
                    s.active_since = ts
                    s.accumulated_time = 0.0
                else:
                    s.accumulated_time = ts - s.active_since
                active_candidates.append((name, z_ioa))
            else:
                s.active_since = None
                s.accumulated_time = 0.0
        
        # Choose active zone by priority order (not by IoA)
        chosen = None
        chosen_ioa = 0.0
        if active_candidates:
            active_map = {n: v for n, v in active_candidates}
            for p in self.cfg.priority:
                if p in active_map:
                    chosen = p
                    chosen_ioa = active_map[p]
                    break
        
        # Hysteresis: зона меняется только после N тиков подряд
        # Если активна новая зона (отличается от текущей), накапливаем счетчик
        if chosen != self.current_activity:
            if chosen == self.candidate_zone:
                # Та же кандидат - накапливаем счетчик
                self.candidate_ticks += 1
            else:
                # Новый кандидат - сбрасываем счетчик
                self.candidate_zone = chosen
                self.candidate_ticks = 1
        else:
            # Активна та же зона - сбрасываем кандидата
            self.candidate_zone = None
            self.candidate_ticks = 0
        
        # Применяем hysteresis: зона меняется только если кандидат держится N тиков
        effective_zone = self.current_activity
        if self.candidate_zone is not None and self.candidate_ticks >= self.cfg.hysteresis_ticks:
            effective_zone = self.candidate_zone
        
        # Confirm activity only if zone has accumulated min_time
        confirmed = None
        if effective_zone is not None:
            zcfg = self.cfg.zones[effective_zone]
            zstate = self.states[effective_zone]
            if zstate.accumulated_time >= zcfg.min_time_sec:
                confirmed = effective_zone
        
        # Handle activity transitions -> emit event when activity ends/changes
        if confirmed != self.current_activity:
            # end previous
            if self.current_activity is not None and self.current_activity_start is not None:
                events.append(ActivityEvent(
                    self.current_activity,
                    self.current_activity_start,
                    ts - self.current_activity_start
                ))
            # start new
            if confirmed is not None:
                self.current_activity = confirmed
                self.current_activity_start = ts
            else:
                self.current_activity = None
                self.current_activity_start = None
        
        return ROIResult(active_zone=confirmed, active_ioa=chosen_ioa, events=events)
    
    def _reset_all(self, ts: float) -> None:
        for s in self.states.values():
            s.active_since = None
            s.accumulated_time = 0.0
            # last_center оставляем: полезно для sleeping после краткой потери


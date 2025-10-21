# risk_model.py
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import time
from typing import Deque, Tuple

_now = time.perf_counter  # relógio monotônico (estável)

@dataclass
class RiskConfig:
    """Parâmetros do modelo de risco."""
    blink_window_s: float = 15.0   # janela deslizante para taxa de piscos
    risk_minutes: float   = 15.0   # minutos de tempo ATIVO para acionar risco
    blink_rate_hi: float  = 60.0   # piscos por minuto considerados altos
    warmup_s: float       = 5.0    # tempo antes de avaliar risco
    max_dt_s: float       = 0.6    # limite para picos de dt (anti saltos)

class RiskModel:
    """
    Regras de risco:
      • blink_rate_hi: limite de piscadas por minuto (janela deslizante)
      • risk_minutes:  minutos de TEMPO ATIVO (apenas quando face_present=True)
      • warmup_s:      segundos de aquecimento antes de avaliar risco

    API:
      - note_blink(t=None): registra um piscar (timestamp opcional)
      - update(face_present: bool) -> (risky, blink_rate_per_min, minutes_on)
      - reset_counters(): zera contadores (piscos/tempo)
    """
    def __init__(self,
                 blink_window_s: float = 15.0,
                 risk_minutes: float   = 15.0,
                 blink_rate_hi: float  = 60.0,
                 warmup_s: float       = 5.0,
                 max_dt_s: float       = 0.6):
        self.cfg = RiskConfig(
            blink_window_s=blink_window_s,
            risk_minutes=risk_minutes,
            blink_rate_hi=blink_rate_hi,
            warmup_s=warmup_s,
            max_dt_s=max_dt_s,
        )

        self.blinks: Deque[float] = deque()   # timestamps de piscos
        self.active_seconds: float = 0.0      # acumula só com face_present=True

        now = _now()
        self._last_t: float = now            # p/ calcular dt entre frames
        self._session_start: float = now

        self.block_mode: bool = False        # estado de risco atual

    # -------- piscos --------
    def note_blink(self, t: float | None = None) -> None:
        """Registra um piscar e mantém a janela deslizante."""
        t = _now() if t is None else t
        self.blinks.append(t)
        self._trim_blinks(t)

    def _trim_blinks(self, t: float) -> None:
        """Remove piscos fora da janela deslizante."""
        win = self.cfg.blink_window_s
        while self.blinks and (t - self.blinks[0]) > win:
            self.blinks.popleft()

    def blink_rate_per_min(self, t=None):
        t = _now() if t is None else t
        # mantém a janela deslizante
        while self.blinks and t - self.blinks[0] > self.window_s:
            self.blinks.popleft()

        if len(self.blinks) < 2:
            return 0.0

        span = max(1e-3, self.blinks[-1] - self.blinks[0])  # segundos
        return len(self.blinks) / span * 60.0

    # -------- tempo --------
    def minutes_on(self) -> float:
        return self.active_seconds / 60.0

    def seconds_on(self) -> float:
        return self.active_seconds

    # -------- controle --------
    def reset_counters(self) -> None:
        """Zera o tempo ativo e a janela de piscos."""
        self.blinks.clear()
        self.active_seconds = 0.0
        now = _now()
        self._last_t = now
        self._session_start = now
        self.block_mode = False

    def set_risk_minutes(self, mins: float) -> None:
        self.cfg.risk_minutes = max(0.0, float(mins))

    # -------- passo de atualização --------
    def update(self, face_present: bool) -> Tuple[bool, float, float]:
        """
        Deve ser chamada a cada frame.
        Se face_present=True, acumula dt em active_seconds.
        Retorna: (risky, blink_rate_per_min, minutes_on)
        """
        t = _now()
        raw_dt = t - (self._last_t or t)
        # anti picos (ex.: pausa de SO, arrasto de janela etc.)
        dt = max(0.0, min(raw_dt, self.cfg.max_dt_s))
        self._last_t = t

        if face_present:
            self.active_seconds += dt

        rate = self.blink_rate_per_min(t)
        mins = self.minutes_on()

        risky = False
        if self.seconds_on() >= self.cfg.warmup_s:
            if rate > self.cfg.blink_rate_hi or mins >= self.cfg.risk_minutes:
                risky = True

        self.block_mode = risky
        return risky, rate, mins

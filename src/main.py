import os
# Silenciar logs chatos do TF/MediaPipe
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["GLOG_minloglevel"] = "2"

import sys
import math
import time
import ctypes
import cv2
import mediapipe as mp

from utils import (
    create_trackbars, get_params, draw_rect,
    panel, text, label_value, badge, eye_aspect_ratio,
    render_controls_legend, COL_ACC, COL_OK, COL_BAD,
    big_alert,
)
from risk_model import RiskModel

# >>> Integração (API local + eventos)
from integration import (
    run_in_thread as start_api,
    update_status,
    log_event,
    set_reset_callback,
)

APP_WIN  = "Alerta Bet BR"
CTRL_WIN = "Controles"

# ---- Parâmetros de anti-ruído e alerta ----
EAR_SMOOTH_N     = 5       # média móvel do EAR (frames)
CLOSED_MIN_S     = 0.12    # duração mínima "fechado" para contar piscar
REFRACTORY_S     = 0.80    # intervalo mínimo entre piscos
BEEP_INTERVAL_S  = 2.0     # intervalo entre beeps enquanto em risco (Windows)
BEEP_FREQ_HZ     = 880
BEEP_DUR_MS      = 150
LEGEND_REFRESH_N = 60      # redesenhar legenda dos controles a cada N frames

# ---- contadores em ESCOPO DE MÓDULO (para usar global no callback/tecla) ----
blink_counter = 0

# ---------- util: fixar janela como always-on-top (Windows) ----------
def pin_window_top(window_title: str) -> None:
    try:
        user32 = ctypes.windll.user32
        SWP_NOSIZE, SWP_NOMOVE, HWND_TOPMOST = 0x0001, 0x0002, -1
        hwnd = user32.FindWindowW(None, window_title)
        if hwnd:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    except Exception:
        pass

# ---------- webcam com fallback de APIs/índices ----------
def open_camera() -> cv2.VideoCapture:
    """Tenta abrir a webcam priorizando DirectShow (Windows) e aceita override via env."""
    preferred = os.getenv("ALERTABET_CAM_INDEX")   # ex: set ALERTABET_CAM_INDEX=0
    try_indices = [int(preferred)] if preferred is not None else [0, 1, 2, 3]

    candidates = []
    # 1) DirectShow primeiro (costuma evitar o bug do MSMF)
    for idx in try_indices:
        candidates.append((idx, cv2.CAP_DSHOW))
    # 2) Sem backend explícito
    for idx in try_indices:
        candidates.append((idx, 0))
    # 3) Qualquer backend
    for idx in try_indices:
        candidates.append((idx, cv2.CAP_ANY))

    for idx, api in candidates:
        cap = cv2.VideoCapture(idx, api) if api != 0 else cv2.VideoCapture(idx)
        if cap.isOpened():
            # testa leitura real (alguns “abrem” mas não entregam frames)
            ok, _ = cap.read()
            if ok:
                print(f"[OK] Camera aberta: index={idx}, api={api}")
                return cap
            cap.release()
        print(f"[FAIL] index={idx}, api={api}")
    raise RuntimeError(
        "Nenhuma câmera pôde ser aberta. "
        "Feche apps que usam a webcam e verifique as permissões de câmera do Windows."
    )

# ---------- janelas e controles ----------
cv2.namedWindow(APP_WIN)
cv2.namedWindow(CTRL_WIN)
create_trackbars(CTRL_WIN)
pin_window_top(CTRL_WIN)

controls_canvas = render_controls_legend()
cv2.imshow(CTRL_WIN, controls_canvas)

# ---------- Haar Cascade ----------
cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
print("Usando Haar Cascade em:", cascade_path)
face_cascade = cv2.CascadeClassifier(cascade_path)
if face_cascade.empty():
    raise FileNotFoundError(f"Não consegui carregar o Haar Cascade em {cascade_path}")

# ---------- MediaPipe ----------
mp_face = mp.solutions.face_mesh
LEFT  = [33,160,158,133,153,144]
RIGHT = [263,387,385,362,380,373]

cap   = open_camera()
model = RiskModel()  # defina warmup_s=5 no risk_model.py para testes mais rápidos

# ---- Inicia API de integração (thread) ----
start_api()  # http://127.0.0.1:8000

help_on        = False
last_beep_time = 0.0

with mp_face.FaceMesh(static_image_mode=False, refine_landmarks=True, max_num_faces=1,
                      min_detection_confidence=0.5, min_tracking_confidence=0.5) as mesh:

    # NÃO recrie blink_counter aqui!
    closed_start_t = None
    last_blink_t   = 0.0
    is_closed      = False
    fps_hist, ear_hist = [], []
    frame_count    = 0
    prev_risky     = False  # para logar evento só na transição

    # callback remoto (POST /reset) — usa 'global' em vez de nonlocal
    def _reset_callback():
        global blink_counter
        blink_counter = 0
        model.reset_counters()
        log_event("reset", "api")
    set_reset_callback(_reset_callback)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t0 = time.perf_counter()
        frame_count += 1

        # --- parâmetros atuais dos sliders ---
        params = get_params(CTRL_WIN)
        model.set_risk_minutes(params["risk_minutes"])  # usar setter do modelo novo
        EAR_low  = params["EAR_thr"]
        EAR_high = EAR_low + 0.03  # histerese

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # ---- Haar (retângulos de rosto) ----
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=params["scaleFactor"],
            minNeighbors=params["minNeighbors"],
            minSize=(params["minSize"], params["minSize"]),
        )

        # ---- MediaPipe (landmarks) ----
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = mesh.process(rgb)

        # considera rosto presente se HAAR OU MediaPipe detectarem
        have_face = bool(res.multi_face_landmarks) or (len(faces) > 0)

        ear = 0.0
        valid_faces = []

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark
            H, W = frame.shape[:2]

            def pts(idx):
                return [(int(lm[i].x * W), int(lm[i].y * H)) for i in idx]

            L, R = pts(LEFT), pts(RIGHT)

            # landmarks dos olhos
            for p in L + R:
                cv2.circle(frame, p, 1, (255, 0, 0), -1)

            # EAR suavizado
            ear_inst = (eye_aspect_ratio(L) + eye_aspect_ratio(R)) / 2.0
            ear_hist = (ear_hist + [ear_inst])[-EAR_SMOOTH_N:]
            ear = sum(ear_hist) / len(ear_hist)

            # piscos robustos
        # --- piscos robustos (dentro do if res.multi_face_landmarks) ---
        tnow = time.perf_counter()

        # entrou no estado "olho fechado"
        if not is_closed and ear < EAR_low:
            is_closed = True
            closed_start_t = tnow

        # saiu do estado "fechado" e voltou a abrir
        elif is_closed and ear > EAR_high:
            closed_dur = (tnow - (closed_start_t or tnow))
            enough_duration = closed_dur >= CLOSED_MIN_S   # 0.12s ~ 3-4 frames
            enough_gap      = (tnow - last_blink_t) >= REFRACTORY_S  # 0.8s

            if enough_duration and enough_gap:
                blink_counter += 1
                last_blink_t = tnow
                model.note_blink(tnow)   # <<< MUITO IMPORTANTE

            is_closed = False
            closed_start_t = None


        # Desenha retângulo se Haar detectou (ajuda a estabilidade visual)
        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
            valid_faces.append((x, y, w, h))
            draw_rect(frame, x, y, w, h)

        # ---- risco (passa se há rosto) ----
        risky, rate, mins = model.update(face_present=have_face)

        # >>> Atualiza API /status
        update_status(
            have_face=bool(have_face),
            faces=int(len(faces)),
            ear=float(ear),
            blink_rate=float(rate),
            minutes_on=float(mins),
            risky=bool(risky),
        )

        # >>> Evento quando entra em risco
        if risky and not prev_risky:
            log_event("risk", f"minutes_on={mins:.2f}; blink_rate={rate:.1f}")
        prev_risky = risky

        # FPS
        fps = 1.0 / max(1e-6, time.perf_counter() - t0)
        fps_hist = (fps_hist + [fps])[-30:]
        fps_avg  = sum(fps_hist) / len(fps_hist)

        # ---- UI principal ----
        H, W = frame.shape[:2]
        panel(frame, 0, 0, W, 40, 0.55)
        text(frame, "Alerta Bet BR", (14, 26), 0.8, COL_ACC, 2)

        px, py, pw, ph = 10, 50, 240, 220
        panel(frame, px, py, pw, ph, 0.55)
        label_value(frame, "FPS",        f"{fps_avg:.1f}",  px+14, py+20)
        label_value(frame, "Faces",      f"{len(valid_faces)}", px+14, py+60)
        label_value(frame, "EAR",        f"{ear:.3f}",      px+14, py+100)
        label_value(frame, "Blinks/min", f"{rate:.1f}",     px+14, py+140)
        label_value(frame, "Tempo (min)",f"{mins:.1f}",     px+14, py+180)

        if risky:
            badge(frame, "RISCO", px+14, py+ph-36, COL_BAD)
            pulse = abs(math.sin(time.perf_counter() * 2.2))
            big_alert(
                frame,
                title="RISCO - PAUSA AGORA",
                subtitle="Faça uma pausa",
                hint="Pressione R para resetar contadores",
                pulse=pulse
            )
            if sys.platform.startswith("win") and (time.perf_counter() - last_beep_time > BEEP_INTERVAL_S):
                try:
                    import winsound
                    winsound.Beep(BEEP_FREQ_HZ, BEEP_DUR_MS)
                except Exception:
                    pass
                last_beep_time = time.perf_counter()
        else:
            badge(frame, "OK", px+14, py+ph-36, COL_OK)

        # Overlay de ajuda (H)
        if help_on:
            w_help, h_help = 420, 180
            panel(frame, W - w_help - 10, 50, w_help, h_help, 0.75)
            text(frame, "Ajuda / Atalhos", (W - w_help + 14, 72), 0.75, COL_ACC, 2)
            lines = [
                "H : Mostrar/ocultar esta ajuda",
                "R : Resetar tempo e contadores",
                "S : Salvar frame (./frame_YYYYMMDD_HHMMSS.png)",
                "Q/ESC : Sair",
                "Dica: aumente 'neighbors' e 'minSize' para reduzir falsos positivos.",
            ]
            y = 96
            for ln in lines:
                text(frame, ln, (W - w_help + 14, y), 0.6)
                y += 24

        cv2.imshow(APP_WIN, frame)
        pin_window_top(CTRL_WIN)

        if frame_count % LEGEND_REFRESH_N == 0:
            cv2.imshow(CTRL_WIN, controls_canvas)

        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord('q')):  # ESC/Q
            break
        elif k in (ord('h'), ord('H')):
            help_on = not help_on
        elif k in (ord('r'), ord('R')):
            blink_counter = 0
            model.reset_counters()
            log_event("reset", "keyboard")
        elif k in (ord('s'), ord('S')):
            ts = time.strftime("%Y%m%d_%H%M%S")
            fn = f"frame_{ts}.png"
            cv2.imwrite(fn, frame)
            print("Frame salvo:", fn)

cap.release()
cv2.destroyAllWindows()

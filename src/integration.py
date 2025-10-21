# src/integration.py
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn

# --- API Fast ---
app = FastAPI(title="Alerta Bet BR API", version="1.0")

# --- Permitir acesso pelo navegador (dashboard local) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Estado global (atualizado pelo main.py) ---
_state = {
    "have_face": False,
    "faces": 0,
    "ear": 0.0,
    "blink_rate": 0.0,
    "blink_count": 0,
    "minutes_on": 0.0,
    "risky": False,
}

# --- Lista de eventos recentes ---
_events = []  # cada item: {"type": "risk", "timestamp": "...", "msg": "..."}

# --- Callback remoto de reset (registrado pelo main.py) ---
_reset_callback = None


# ============================================================
# Funções utilitárias para o main.py chamar
# ============================================================

def update_status(**kwargs):
    """Atualiza o estado global (chamado pelo main.py a cada frame)."""
    _state.update({k: v for k, v in kwargs.items() if k in _state})


def log_event(event_type: str, msg: str = ""):
    """Adiciona um evento à lista (visível em /events)."""
    _events.append({
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "msg": msg,
    })
    # mantém até 500 eventos recentes
    if len(_events) > 500:
        del _events[:-500]


def set_reset_callback(fn):
    """Permite que o main.py registre uma função para reset remoto."""
    global _reset_callback
    _reset_callback = fn


def run_in_thread(host="127.0.0.1", port=8000):
    """Inicia o servidor FastAPI em thread paralela (não bloqueante)."""
    def _run():
        uvicorn.run(app, host=host, port=port, log_level="error")
    th = threading.Thread(target=_run, daemon=True)
    th.start()
    print(f"[OK] API local rodando em http://{host}:{port}")


# ============================================================
# Rotas HTTP
# ============================================================

@app.get("/status")
def get_status():
    """Retorna o estado atual do sistema (para o dashboard)."""
    return _state


@app.get("/events")
def get_events():
    """Retorna a lista de eventos recentes."""
    return _events


@app.post("/reset")
def reset():
    """Reset remoto via dashboard."""
    if callable(_reset_callback):
        try:
            _reset_callback()
        except Exception as e:
            print("[ERRO] Callback de reset falhou:", e)
    log_event("reset", "via API")
    _state["blink_rate"] = 0.0
    _state["blink_count"] = 0
    return {"ok": True, "msg": "Reset executado"}


# ============================================================
# Execução direta (opcional para testes)
# ============================================================
if __name__ == "__main__":
    run_in_thread()
    import time
    while True:
        time.sleep(1)

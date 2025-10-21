# utils.py
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ==== Paleta de cores ====
COL_BG   = (16, 16, 16)
COL_TXT  = (245, 245, 245)
COL_ACC  = (120, 190, 255)
COL_OK   = (60, 190, 120)
COL_WARN = (255, 200, 0)
COL_BAD  = (255, 80, 80)
COL_DIM  = (180, 180, 180)

# ---------------- Base UI helpers ----------------
def _overlay_alpha(dst, src, x, y, alpha=0.7):
    """Sobrepõe 'src' em 'dst' com alpha (BGR)."""
    h, w = src.shape[:2]
    # Proteção contra recorte fora da imagem
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x0 >= x1 or y0 >= y1:
        return
    roi = dst[y0:y1, x0:x1]
    src_crop = src[(y0 - y):(y0 - y) + (y1 - y0), (x0 - x):(x0 - x) + (x1 - x0)]
    cv2.addWeighted(src_crop, alpha, roi, 1 - alpha, 0, roi)

def panel(frame, x, y, w, h, alpha=0.65):
    box = np.full((h, w, 3), COL_BG, dtype=np.uint8)
    _overlay_alpha(frame, box, x, y, alpha)
    return (x, y, w, h)

def text(frame, txt, org, scale=0.7, color=COL_TXT, thick=2):
    cv2.putText(frame, txt, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)

def label_value(frame, label, value, x, y, w=250, line=26):
    text(frame, label, (x, y), 0.65, COL_DIM, 1)
    text(frame, value, (x, y + line), 0.8, COL_TXT, 2)

def badge(frame, text_str, x, y, color=COL_OK):
    padx, pady = 10, 8
    (tw, th), _ = cv2.getTextSize(text_str, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    bw, bh = tw + padx * 2, th + pady * 2
    box = np.full((bh, bw, 3), color, dtype=np.uint8)
    _overlay_alpha(frame, box, x, y, 0.9)
    text(frame, text_str, (x + padx, y + bh - pady - 2), 0.7, (0, 0, 0), 2)

# ---------------- Trackbars ----------------
def create_trackbars(win):
    # Haar
    cv2.createTrackbar("scaleFactor x100", win, 120, 200, lambda x: None)  # 1.20
    cv2.createTrackbar("minNeighbors",     win,   6,  15, lambda x: None)
    cv2.createTrackbar("minSize(px)",      win, 100, 200, lambda x: None)
    # Risco/olhos
    cv2.createTrackbar("EAR_thr x1000",    win,  21, 100, lambda x: None)  # 0.21
    cv2.createTrackbar("risk_min",         win,   1,  60, lambda x: None)  # 1 min (teste fluido)

def get_params(win):
    sf  = max(1.01, cv2.getTrackbarPos("scaleFactor x100", win) / 100.0)
    mn  = cv2.getTrackbarPos("minNeighbors", win)
    ms  = cv2.getTrackbarPos("minSize(px)", win)
    ear = cv2.getTrackbarPos("EAR_thr x1000", win) / 1000.0
    rkm = max(1, cv2.getTrackbarPos("risk_min", win))
    return dict(scaleFactor=sf, minNeighbors=mn, minSize=ms,
                EAR_thr=ear, risk_minutes=rkm)

# ---------------- Visuais diversos ----------------
def draw_rect(frame, x, y, w, h, color=(120, 255, 120)):
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

def euclidean(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))

def eye_aspect_ratio(eye_pts):
    p1, p2, p3, p4, p5, p6 = eye_pts
    A = euclidean(p2, p6)
    B = euclidean(p3, p5)
    C = euclidean(p1, p4)
    return (A + B) / (2.0 * C + 1e-6)

# ---------------- Render (Pillow) ----------------
def _pick_font(size, bold=False):
    """Escolhe uma fonte TrueType disponível (com acentos)."""
    prefs = [
        (r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
        (r"C:\Windows\Fonts\arialbd.ttf"  if bold else r"C:\Windows\Fonts\arial.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for p in prefs:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def render_controls_legend(w=520, h=240):
    """
    Painel compacto e amigável com explicações dos controles (com acentos).
    Retorna imagem BGR (numpy) para cv2.imshow.
    """
    def bgr_to_rgb(c): return (c[2], c[1], c[0])

    bg_rgb  = (30, 30, 30)
    acc_rgb = bgr_to_rgb(COL_ACC)
    txt_rgb = bgr_to_rgb(COL_TXT)
    dim_rgb = (200, 200, 200)

    img  = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    font_title = _pick_font(18, bold=True)
    font_label = _pick_font(14, bold=True)
    font_body  = _pick_font(13, bold=False)

    draw.text((12, 10), "Como usar os controles", fill=acc_rgb, font=font_title)

    linhas = [
        ("scaleFactor:", "Precisão da busca de rosto (1,10–1,40 recomendado)."),
        ("minNeighbors:", "Confiança para aceitar rosto (↑ = menos falsos)."),
        ("minSize:", "Ignora rostos menores que esse valor (px)."),
        ("EAR_thr:", "Sensibilidade para piscar (0,18–0,24 costuma ir bem)."),
        ("risk_min:", "Minutos até acionar alerta por tempo prolongado."),
        ("Atalhos:", "H = Ajuda | R = Reset | S = Salvar frame | Q/ESC = Sair"),
    ]
    y = 40
    for titulo, texto in linhas:
        draw.text((14, y), titulo, fill=txt_rgb, font=font_label)
        draw.text((140, y), texto, fill=dim_rgb, font=font_body)
        y += 30

    arr = np.array(img)[:, :, ::-1].copy()  # RGB->BGR
    return arr

# -------- Helpers compatíveis com Pillow 10+ --------
def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """
    Retorna (w, h) do texto usando textbbox quando disponível (Pillow >=10),
    caindo para textsize em versões antigas.
    """
    if hasattr(draw, "textbbox"):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return (right - left), (bottom - top)
    # Pillow <10
    return draw.textsize(text, font=font)

def _wrap_text(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        tw, _ = _text_size(draw, trial, font)
        if tw <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

# ---- Alerta grande (Pillow, com acentos e dica no canto inferior direito) ----
def big_alert(frame,
              title="RISCO - PAUSA AGORA",
              subtitle="Você está há muito tempo focado. Faça uma pausa e retome com clareza.",
              hint="Pressione R para resetar contadores",
              pulse=0.0):
    """
    Desenha alerta grande, translúcido e centralizado com acentos corretos (Pillow).
    A dica fica no canto inferior direito do banner.
    Modifica 'frame' in-place.
    """
    H, W = frame.shape[:2]

    # BGR->RGB para trabalhar com Pillow
    base_rgb = frame[:, :, ::-1]
    base_img = Image.fromarray(base_rgb)
    overlay  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw     = ImageDraw.Draw(overlay)

    # Área do banner
    box_h = int(H * 0.36)
    box_h = max(160, min(box_h, int(H * 0.6)))
    box_y = max(40, H - box_h - 20)  # 20 px acima da borda inferior

    # Cor pulsante (vermelho)
    c1 = np.array([255, 64, 64], dtype=np.float32)
    c0 = np.array([220, 40, 40], dtype=np.float32)
    c  = (c0 * (1.0 - pulse) + c1 * pulse).astype(int)
    rect_color = (int(c[0]), int(c[1]), int(c[2]), 225)

    # Banner arredondado
    radius = 18
    draw.rounded_rectangle([20, box_y, W - 20, box_y + box_h], radius, fill=rect_color)

    pad_x   = 36
    inner_w = W - 2 * (pad_x + 20)

    # Título
    title_size = max(28, int(W / 18))
    font_title = _pick_font(title_size, bold=True)
    font_sub   = _pick_font(max(20, int(W / 45)))
    font_hint  = _pick_font(18)

    # Centraliza título
    tw, th = _text_size(draw, title, font_title)
    tx = (W - tw) // 2
    ty = box_y + 24
    # sombra
    for off in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
        draw.text((tx + off[0], ty + off[1]), title, fill=(0, 0, 0, 220), font=font_title)
    draw.text((tx, ty), title, fill=(255, 255, 255, 255), font=font_title)

    # Subtítulo (até 2 linhas)
    lines = _wrap_text(draw, subtitle, font_sub, inner_w)[:2]
    y = ty + th + 18
    for ln in lines:
        lw, lh = _text_size(draw, ln, font_sub)
        draw.text(((W - lw) // 2, y), ln, fill=(255, 255, 255, 235), font=font_sub)
        y += lh + 6

    # Dica no canto inferior direito (dentro do banner)
    hw, hh = _text_size(draw, hint, font_hint)
    hx = W - hw - 36
    hy = box_y + box_h - hh - 18
    draw.rounded_rectangle([hx - 10, hy - 6, hx + hw + 10, hy + hh + 6], 10, fill=(30, 30, 30, 200))
    draw.text((hx, hy), hint, fill=(255, 255, 255, 255), font=font_hint)

    # Composição e volta para BGR
    composed = Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")
    frame[:, :] = np.array(composed)[:, :, ::-1]

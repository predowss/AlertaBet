# face_id.py
# Reconhecimento facial simples com LBPH (OpenCV-contrib)
# Estrutura esperada:
# src/data/faces/
#   ├── PessoaA/  img1.jpg, img2.jpg, ...
#   └── PessoaB/  img1.png, img2.png, ...

import os
from typing import List, Tuple, Optional

import cv2
import numpy as np


# ---------------- util ----------------
def _has_cv2_face() -> bool:
    return hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create")


def _preprocess(gray: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """Equaliza e redimensiona para tamanho consistente."""
    if gray is None:
        raise ValueError("Imagem vazia em _preprocess")
    if len(gray.shape) == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    # equalização de histograma ajuda na luz
    gray = cv2.equalizeHist(gray)
    if size is not None:
        gray = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    return gray


# ---------------- API pública ----------------
def load_lbph_model(
    data_dir: str = "src/data/faces",
    face_size: Tuple[int, int] = (120, 120),
    min_images_per_person: int = 2,
) -> Tuple[Optional[cv2.face_LBPHFaceRecognizer], List[str]]:
    """
    Cria e treina um reconhecedor LBPH com as imagens do diretório.
    Retorna (recognizer or None, lista_de_nomes).

    - face_size: todas as imagens são normalizadas para este tamanho
    - min_images_per_person: pastas com menos imagens são ignoradas
    """
    if not _has_cv2_face():
        # OpenCV-contrib não instalado
        return None, []

    if not os.path.isdir(data_dir):
        return None, []

    imgs: List[np.ndarray] = []
    labels: List[int] = []
    names: List[str] = []
    label_id = 0

    # somente extensões comuns
    valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".pgm"}

    for name in sorted(os.listdir(data_dir)):
        person_dir = os.path.join(data_dir, name)
        if not os.path.isdir(person_dir):
            continue

        # coleta imagens da pessoa
        person_imgs = []
        for f in sorted(os.listdir(person_dir)):
            ext = os.path.splitext(f)[1].lower()
            if ext not in valid_ext:
                continue
            p = os.path.join(person_dir, f)
            img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            try:
                img = _preprocess(img, face_size)
            except Exception:
                continue
            person_imgs.append(img)

        if len(person_imgs) < min_images_per_person:
            # ignora classes com poucas amostras
            continue

        # adiciona ao dataset
        for im in person_imgs:
            imgs.append(im)
            labels.append(label_id)

        names.append(name)
        label_id += 1

    if not imgs or not names:
        return None, []

    # treina LBPH
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=123.0
    )
    recognizer.train(imgs, np.array(labels, dtype=np.int32))
    return recognizer, names


def predict(
    rec: Optional[cv2.face_LBPHFaceRecognizer],
    names: List[str],
    gray_face: np.ndarray,
    face_size: Tuple[int, int] = (120, 120),
) -> Tuple[str, float]:
    """
    Retorna (nome, confianca). Para LBPH, **confianca menor = melhor**.
    Se não houver modelo, devolve ("desconhecido", 999.0).
    """
    if rec is None or not names:
        return "desconhecido", 999.0

    try:
        roi = _preprocess(gray_face, face_size)
    except Exception:
        return "desconhecido", 999.0

    label, conf = rec.predict(roi)
    if 0 <= label < len(names):
        return names[label], float(conf)
    return "desconhecido", float(conf)

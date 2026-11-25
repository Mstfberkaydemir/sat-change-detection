"""Değişim tespiti servisi (iskelet).

Şimdilik ml/ klasöründeki klasik baseline (görüntü farkı + Otsu) kullanılır. Aşama 5'te eğitilmiş
ONNX modeli, aynı `ChangeDetector` arayüzünü uygulayan bir sınıf olarak buraya eklenecek;
endpoint kodu değişmeyecek.
"""
from dataclasses import dataclass
from typing import Optional, Protocol

import cv2
import numpy as np


class ImageDecodeError(ValueError):
    """Dosya geçerli bir görüntü olarak çözülemedi."""


def decode_image(data: bytes) -> np.ndarray:
    """Bayt dizisinden (H, W, 3) uint8 BGR görüntü çözer; bozuksa ImageDecodeError."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ImageDecodeError("Dosya geçerli bir görüntü değil veya bozuk")
    return img


def read_image(path) -> np.ndarray:
    # np.fromfile: Windows'ta Türkçe karakterli yollarda cv2.imread'in başarısızlığını önler
    return decode_image(np.fromfile(str(path), dtype=np.uint8).tobytes())


def encode_png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("PNG kodlanamadı")
    return buf.tobytes()


class ChangeDetector(Protocol):
    def predict(self, t1: np.ndarray, t2: np.ndarray) -> np.ndarray:
        """(H, W) uint8, değerler 0/1 döndürür."""
        ...


class ClassicDiffDetector:
    def __init__(self, blur: int = 5, open_k: int = 3, min_thr: int = 20):
        self.blur, self.open_k, self.min_thr = blur, open_k, min_thr

    def predict(self, t1: np.ndarray, t2: np.ndarray) -> np.ndarray:
        delta = t2.astype(np.float32) - t1.astype(np.float32)
        delta -= np.median(delta.reshape(-1, 3), axis=0)  # global aydınlık/renk kaymasını gider
        mag = np.clip(np.sqrt((delta ** 2).sum(axis=2)), 0, 255).astype(np.uint8)
        if self.blur > 1:
            mag = cv2.GaussianBlur(mag, (self.blur, self.blur), 0)
        otsu, _ = cv2.threshold(mag, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask = (mag > max(float(otsu), float(self.min_thr))).astype(np.uint8)
        if self.open_k > 1:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((self.open_k, self.open_k), np.uint8))
        return mask


@dataclass
class DetectionResult:
    mask: np.ndarray  # (H, W) uint8, 0/1
    changed_pixels: int
    change_percentage: float  # 0-100


def run_detection(t1: np.ndarray, t2: np.ndarray, detector: Optional[ChangeDetector] = None) -> DetectionResult:
    """T2, T1'den farklı boyuttaysa T1 boyutuna ölçeklenir (hizalama adımının basit hâli)."""
    if t1.shape[:2] != t2.shape[:2]:
        t2 = cv2.resize(t2, (t1.shape[1], t1.shape[0]), interpolation=cv2.INTER_AREA)
    detector = detector or ClassicDiffDetector()
    mask = detector.predict(t1, t2).astype(np.uint8)
    changed = int(mask.sum())
    return DetectionResult(mask=mask, changed_pixels=changed, change_percentage=100.0 * changed / mask.size)

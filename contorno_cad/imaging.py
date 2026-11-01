"""Leitura de fotografias e extração observável de contornos, em pixels."""
from .i18n import t
from io import BytesIO
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


def read_image(data: bytes) -> np.ndarray:
    if len(data) > 30 * 1024 * 1024:
        raise ValueError(t('Imagem acima do limite de 30 MB.'))
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in {"JPEG", "PNG"}:
                raise ValueError(t('Envie uma fotografia JPEG ou PNG.'))
            if image.width * image.height > 24_000_000:
                raise ValueError(t('Imagem acima de 24 megapixels; reduza a resolução.'))
            return np.asarray(ImageOps.exif_transpose(image).convert("RGB")).copy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError(t('Não foi possível ler a fotografia. Envie um JPEG ou PNG válido e completo.')) from exc


def png_bytes(rgb: np.ndarray) -> bytes:
    output = BytesIO()
    Image.fromarray(rgb).save(output, format="PNG")
    return output.getvalue()


def process_image(rgb, settings=None):
    settings = settings or {}
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = map(int, settings.get("crop", [0, 0, width, height]))
    x0, x1 = max(0, x0), min(width, x1)
    y0, y1 = max(0, y0), min(height, y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        raise ValueError(t('Recorte muito pequeno ou invertido.'))
    crop = rgb[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=float(settings.get("contrast", 1.0)), beta=float(settings.get("brightness", 0)))
    blur = int(settings.get("blur", 3)) | 1
    if blur > 1:
        gray = cv2.GaussianBlur(gray, (min(blur, 21), min(blur, 21)), 0)
    method = settings.get("method", "Canny")
    if method == "Canny":
        mask = cv2.Canny(gray, int(settings.get("low", 50)), int(settings.get("high", 150)))
    elif method in {"Escuro", "Claro"}:
        flag = cv2.THRESH_BINARY_INV if method == "Escuro" else cv2.THRESH_BINARY
        threshold = int(settings.get("threshold", 0))
        _, mask = cv2.threshold(gray, threshold, 255, flag | (cv2.THRESH_OTSU if threshold == 0 else 0))
    elif method == "Fundo colorido":
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
        mask = np.where((hsv[:, :, 1] < int(settings.get("saturation", 105))) & (gray > 65), 255, 0).astype(np.uint8)
    else:
        raise ValueError(t('Método de detecção desconhecido.'))
    close = int(settings.get("close", 3))
    if close > 0:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_min = float(settings.get("min_area", 100))
    contours = sorted((c + np.array([[[x0, y0]]]) for c in contours if cv2.contourArea(c) >= area_min), key=cv2.contourArea, reverse=True)[:50]
    overlay = rgb.copy()
    for index, contour in enumerate(contours):
        cv2.drawContours(overlay, [contour], -1, (0, 210, 160), 2)
        p = contour.reshape(-1, 2)[0]
        cv2.putText(overlay, str(index + 1), tuple(p), cv2.FONT_HERSHEY_SIMPLEX, .7, (20, 30, 240), 2)
    processed = np.zeros((height, width), np.uint8)
    processed[y0:y1, x0:x1] = mask
    return {"gray": gray, "mask": processed, "contours": contours, "overlay": overlay, "crop": [x0, y0, x1, y1]}


def contour_points(contour, tolerance=2.0):
    points = cv2.approxPolyDP(contour, float(tolerance), True).reshape(-1, 2)
    if len(points) < 3:
        raise ValueError(t('O contorno tem menos de três pontos. Reduza a simplificação.'))
    return [{"x": float(x), "y": float(y), "kind": "line"} for x, y in points]


def right_wall(contour, samples=12, trim_top=.09, trim_bottom=.06):
    """Amostra a silhueta direita; perspectiva/escala continuam sendo hipóteses."""
    x, y, w, h = cv2.boundingRect(contour)
    mask = np.zeros((y + h + 2, x + w + 2), np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, cv2.FILLED)
    points = []
    for row in np.linspace(y + h * (1 - trim_bottom), y + h * trim_top, samples):
        rr = int(row)
        cols = np.flatnonzero(mask[rr])
        if len(cols):
            points.append({"x": float(cols[-1]), "y": float(rr), "kind": "line"})
    if len(points) < 2:
        raise ValueError(t('Não foi possível amostrar a lateral deste contorno.'))
    return points, {"axis_x": x + w / 2, "baseline_y": y + h - 1, "height_px": h, "bounds": [x, y, w, h]}

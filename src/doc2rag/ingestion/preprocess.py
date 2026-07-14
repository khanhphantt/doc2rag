from __future__ import annotations

import cv2
import numpy as np


def preprocess_page(image: np.ndarray) -> np.ndarray:
    """Deskew, denoise, and normalize contrast on a scanned page.

    Returns an RGB uint8 array of the same shape family as the input, ready
    for layout detection / OCR. Keeps output in RGB (not binarized) since
    PaddleOCR performs better on grayscale-ish photos than on hard binary
    thresholds for real-world scans.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    deskewed = _deskew(denoised)
    normalized = cv2.normalize(deskewed, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.cvtColor(normalized, cv2.COLOR_GRAY2RGB)


def _deskew(gray: np.ndarray) -> np.ndarray:
    inverted = cv2.bitwise_not(gray)
    thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.1:
        return gray

    h, w = gray.shape
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

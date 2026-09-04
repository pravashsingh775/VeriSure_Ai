import io
import cv2
import numpy as np


def create_test_amul_image(
    tamper_seal: bool = False,
    corrupt_barcode: bool = False,
    blur: bool = False,
    glare: bool = False
) -> np.ndarray:
    """
    Synthesizes a structured test milk pouch graphic with Amul Taaza visual elements,
    text fields, heat-seal crimps, and barcode for deterministic testing.
    """
    h, w = 800, 600
    # Light sky blue background (BGR: 245, 220, 180)
    img = np.full((h, w, 3), (245, 220, 180), dtype=np.uint8)

    # White/cream lower container section
    img[350:720, :] = (240, 240, 240)

    # Top Heat-Seal Crimp Band (0 to 60px)
    if not tamper_seal:
        # Periodic crimp ridges
        for y in range(5, 55, 4):
            cv2.line(img, (0, y), (w, y), (210, 180, 140), 2)
    else:
        # Tampered: smooth / melted irregular patch
        cv2.rectangle(img, (50, 5), (w - 50, 50), (230, 210, 190), -1)

    # Amul Red Logo Arc & Text (Top-Center)
    cv2.circle(img, (300, 140), 65, (30, 30, 200), -1)
    cv2.putText(img, "Amul", (230, 155), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 2.2, (255, 255, 255), 4)

    # "The Taste of India" tagline
    cv2.putText(img, "The Taste of India", (210, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 180), 2)

    # "TAAZA" bold product title
    cv2.putText(img, "TAAZA", (180, 280), cv2.FONT_HERSHEY_DUPLEX, 2.4, (220, 50, 30), 5)
    cv2.putText(img, "HOMOGENISED TONED MILK", (130, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2)

    # Nutrition details
    cv2.putText(img, "FAT: 3.0% min | SNF: 8.5% min", (160, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
    cv2.putText(img, "Net Qty: 1L", (100, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(img, "MRP Rs. 72.00 (Incl. of all taxes)", (100, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    cv2.putText(img, "FSSAI Lic No. 10012021000071", (100, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(img, "Batch No: TAZ-2026-B82", (100, 560), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)

    # Barcode representation
    if not corrupt_barcode:
        # Draw vertical barcode stripes
        bx, by, bw, bh = 360, 430, 180, 80
        cv2.rectangle(img, (bx - 5, by - 5), (bx + bw + 5, by + bh + 25), (255, 255, 255), -1)
        for x in range(bx, bx + bw, 4):
            thick = 1 if (x % 3 == 0) else 2
            cv2.line(img, (x, by), (x, by + bh), (0, 0, 0), thick)
        cv2.putText(img, "8901262010060", (bx + 10, by + bh + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # Bottom Heat-Seal Crimp Band
    if not tamper_seal:
        for y in range(h - 55, h - 5, 4):
            cv2.line(img, (0, y), (w, y), (200, 200, 200), 2)

    # Glare simulation if requested
    if glare:
        cv2.circle(img, (300, 300), 120, (255, 255, 255), -1)

    # Blur simulation if requested
    if blur:
        img = cv2.GaussianBlur(img, (45, 45), 0)

    return img


def get_image_bytes(img: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

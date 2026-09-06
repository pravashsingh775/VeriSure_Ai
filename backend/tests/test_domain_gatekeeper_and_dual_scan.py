import os

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.ai.domain.gatekeeper import DomainGatekeeperEngine
from backend.app.main import app


def create_synthetic_diagram_image():
    """Generates an image mimicking a software architecture diagram (white background, black boxes and lines)."""
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    # Draw flowchart boxes
    cv2.rectangle(img, (100, 100), (300, 200), (0, 0, 0), 2)
    cv2.putText(img, "API GATEWAY", (120, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv2.rectangle(img, (500, 100), (700, 200), (0, 0, 0), 2)
    cv2.putText(img, "DATABASE", (530, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # Connecting arrow
    cv2.arrowedLine(img, (300, 150), (500, 150), (0, 0, 0), 2)
    return img


def create_synthetic_packaging_image(color="red", brand_text="AMUL GOLD"):
    """Generates an image mimicking a dairy pouch with physical background and packaging graphics."""
    img = np.ones((600, 450, 3), dtype=np.uint8) * 230
    if color == "red":
        cv2.rectangle(img, (50, 80), (400, 520), (30, 30, 180), -1)  # Red for Amul Gold
    elif color == "blue":
        cv2.rectangle(img, (50, 80), (400, 520), (180, 100, 30), -1)  # Blue for Amul Taaza
    else:
        cv2.rectangle(img, (50, 80), (400, 520), (50, 160, 50), -1)

    # Brand text
    cv2.putText(img, brand_text, (80, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return img


def test_domain_gatekeeper_rejects_architecture_diagram():
    diagram_img = create_synthetic_diagram_image()
    ocr_text = "System Architecture Diagram API Gateway Service Database Pipeline"

    is_pkg, cat, conf = DomainGatekeeperEngine.is_physical_packaging(diagram_img, ocr_text)
    assert not is_pkg, "System architecture diagram must be recognized as non-packaging!"
    assert "DIAGRAM" in cat, f"Category should reflect diagram, got: {cat}"


def test_domain_gatekeeper_rejects_mother_dairy_competitor_brand():
    pouch_img = create_synthetic_packaging_image(brand_text="MOTHER DAIRY")
    ocr_text = "MOTHER DAIRY TONED MILK FULL CREAM PASTEURISED"

    brand_info = DomainGatekeeperEngine.detect_brand(pouch_img, ocr_text)
    assert not brand_info["is_supported"], "Mother Dairy must be flagged as unsupported competitor brand!"
    assert brand_info["brand"] == "Mother Dairy"
    assert "competitor" in brand_info["reason"].lower() or "mother dairy" in brand_info["reason"].lower()


def test_domain_gatekeeper_accepts_authentic_amul_brand():
    pouch_img = create_synthetic_packaging_image(color="red", brand_text="AMUL GOLD")
    ocr_text = "AMUL GOLD FULL CREAM MILK GCMMF ANAND"

    is_pkg, cat, _ = DomainGatekeeperEngine.is_physical_packaging(pouch_img, ocr_text)
    assert is_pkg, "Amul pouch should be accepted as physical packaging."

    brand_info = DomainGatekeeperEngine.detect_brand(pouch_img, ocr_text)
    assert brand_info["is_supported"], "Amul must be accepted as supported brand."
    assert brand_info["brand"] == "Amul"


@pytest.mark.anyio
async def test_upload_single_diagram_rejection_api():
    """Verifies that uploading an architecture diagram to /upload does not match Amul Gold and yields INSUFFICIENT_EVIDENCE."""
    diagram_img = create_synthetic_diagram_image()
    _, buf = cv2.imencode(".png", diagram_img)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        files = {
            "file": ("architecture_diagram.png", buf.tobytes(), "image/png")
        }
        res = await client.post("/api/v1/scans/upload", files=files, data={"view_type": "FRONT"})
        assert res.status_code == 201
        data = res.json()
        assert data["decision"] is not None
        assert data["decision"]["state"] in ["INSUFFICIENT_EVIDENCE", "UNSUPPORTED_PRODUCT"]
        # Must NOT identify as Amul Gold!
        assert data.get("identified_product_name") is None, "Diagram must not be identified as Amul Gold!"


@pytest.mark.anyio
async def test_upload_dual_scan_front_and_back_api():
    """Verifies that uploading Front and Back together to /upload-dual processes both images in one session."""
    # Use real reference images from data/storage/references/ if available
    ref_front_path = "data/storage/references/amul_taaza_500ml_front.jpg"
    ref_back_path = "data/storage/references/amul_taaza_500ml_back.jpg"

    if os.path.exists(ref_front_path) and os.path.exists(ref_back_path):
        with open(ref_front_path, "rb") as f:
            front_bytes = f.read()
        with open(ref_back_path, "rb") as f:
            back_bytes = f.read()
    else:
        # Fallback to synthetic packaging
        _, b1 = cv2.imencode(".png", create_synthetic_packaging_image(color="blue", brand_text="AMUL TAAZA"))
        _, b2 = cv2.imencode(".png", create_synthetic_packaging_image(color="blue", brand_text="8901262010060 FSSAI 10012021000071"))
        front_bytes = b1.tobytes()
        back_bytes = b2.tobytes()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        files = {
            "file_front": ("front_pouch.jpg", front_bytes, "image/jpeg"),
            "file_back": ("back_pouch.jpg", back_bytes, "image/jpeg")
        }
        res = await client.post("/api/v1/scans/upload-dual", files=files)
        assert res.status_code == 201
        data = res.json()

        # Check that both images were stored and analyzed
        assert len(data["images"]) == 2, f"Dual scan must have exactly 2 images, got: {len(data['images'])}"
        view_types = [img["view_type"] for img in data["images"]]
        assert "FRONT" in view_types
        assert "BACK" in view_types

        # Check that evidences were generated
        assert len(data["evidences"]) > 5
        assert data["decision"] is not None
        assert data["report_url"] is not None


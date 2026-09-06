import hashlib
from pathlib import Path
from typing import Any

import cv2
import imagehash
import numpy as np
from PIL import Image


def compute_sha256(data: bytes | str | Path) -> str:
    """Computes SHA-256 hexadecimal digest from raw bytes or file path."""
    if isinstance(data, (str, Path)):
        with open(data, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    elif isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    else:
        raise ValueError("Data must be bytes or a valid file path")


def compute_perceptual_hashes(img: np.ndarray | Image.Image) -> dict[str, str]:
    """Computes pHash, dHash, and wHash for a given BGR OpenCV image or PIL Image."""
    if isinstance(img, np.ndarray):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
    else:
        pil_img = img

    ph = str(imagehash.phash(pil_img))
    dh = str(imagehash.dhash(pil_img))
    wh = str(imagehash.whash(pil_img))

    return {
        "phash": ph,
        "dhash": dh,
        "whash": wh
    }


def compute_hamming_distance(hash1_str: str, hash2_str: str) -> int:
    """Computes Hamming distance between two hexadecimal hash strings of equal length."""
    h1 = imagehash.hex_to_hash(hash1_str)
    h2 = imagehash.hex_to_hash(hash2_str)
    return h1 - h2


class DuplicateDetector:
    """
    Robust duplicate and near-duplicate detector.
    - Exact duplicate: Identical SHA-256
    - Perceptual duplicate: pHash Hamming distance <= duplicate_threshold (default 4)
    - Near-duplicate: pHash Hamming distance <= near_duplicate_threshold (default 10)
    """

    def __init__(self, duplicate_threshold: int = 4, near_duplicate_threshold: int = 10):
        self.duplicate_threshold = duplicate_threshold
        self.near_duplicate_threshold = near_duplicate_threshold
        self.sha_index: dict[str, str] = {}  # sha256 -> image_id
        self.phash_index: dict[str, str] = {}  # image_id -> phash_str
        self.dhash_index: dict[str, str] = {}  # image_id -> dhash_str
        self.canonical_records: dict[str, dict[str, Any]] = {}
        self.duplicate_sources: dict[str, list[dict[str, Any]]] = {}  # canonical_id -> list of dup sources

    def check_duplicate(
        self,
        sha256_hash: str,
        phash_str: str
    ) -> tuple[bool, bool, str | None, int]:
        """
        Evaluates whether a candidate image is an exact or perceptual duplicate.
        Returns:
            (is_duplicate, is_exact, canonical_id, min_distance)
        """
        # 1. Exact SHA-256 match
        if sha256_hash in self.sha_index:
            canonical_id = self.sha_index[sha256_hash]
            return True, True, canonical_id, 0

        # 2. Perceptual hash comparison
        min_dist = 999
        closest_canonical_id = None

        cand_ph = imagehash.hex_to_hash(phash_str)
        for canon_id, canon_ph_str in self.phash_index.items():
            canon_ph = imagehash.hex_to_hash(canon_ph_str)
            dist = cand_ph - canon_ph
            if dist < min_dist:
                min_dist = dist
                closest_canonical_id = canon_id

        if min_dist <= self.duplicate_threshold and closest_canonical_id is not None:
            return True, False, closest_canonical_id, min_dist

        return False, False, closest_canonical_id, min_dist

    def is_near_duplicate(self, phash_str: str) -> tuple[bool, str | None, int]:
        """Checks if an image is a near-duplicate variation."""
        cand_ph = imagehash.hex_to_hash(phash_str)
        min_dist = 999
        closest_id = None
        for canon_id, canon_ph_str in self.phash_index.items():
            dist = cand_ph - imagehash.hex_to_hash(canon_ph_str)
            if dist < min_dist:
                min_dist = dist
                closest_id = canon_id

        if closest_id and min_dist <= self.near_duplicate_threshold:
            return True, closest_id, min_dist
        return False, closest_id, min_dist

    def register_canonical(
        self,
        image_id: str,
        sha256_hash: str,
        hashes: dict[str, str],
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Registers an image as a canonical reference."""
        self.sha_index[sha256_hash] = image_id
        self.phash_index[image_id] = hashes["phash"]
        self.dhash_index[image_id] = hashes.get("dhash", "")
        self.canonical_records[image_id] = {
            "image_id": image_id,
            "sha256": sha256_hash,
            "hashes": hashes,
            "metadata": metadata or {}
        }
        if image_id not in self.duplicate_sources:
            self.duplicate_sources[image_id] = []

    def record_duplicate(
        self,
        canonical_id: str,
        source_url: str,
        source_domain: str,
        source_type: str,
        sha256_hash: str,
        distance: int
    ) -> None:
        """Records a duplicate occurrence under its canonical reference."""
        if canonical_id not in self.duplicate_sources:
            self.duplicate_sources[canonical_id] = []

        self.duplicate_sources[canonical_id].append({
            "source_url": source_url,
            "source_domain": source_domain,
            "source_type": source_type,
            "sha256": sha256_hash,
            "distance": distance
        })


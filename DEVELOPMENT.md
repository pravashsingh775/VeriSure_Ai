# VeriSure AI — Developer & Contributor Guide

This document outlines engineering conventions, development workflows, testing procedures, and the process for adding new replaceable evidence engines to the VeriSure AI platform.

---

## 1. Engineering Principles & Code Conventions

1. **Modular Monolith**: Keep domain logic isolated in `backend/app/services/` and `backend/app/ai/`. Do not introduce unnecessary microservices.
2. **Explicit Interfaces**: All AI and CV engines must inherit from abstract base classes in `backend/app/ai/contracts.py` and emit standardized `EvidenceObject` records.
3. **No Magic Numbers**: Thresholds and weights must reside in `backend/app/core/config.py` or versioned model metadata.
4. **Honest Outputs**: Never return placeholder confidence values, fake OCR text, or manufactured accuracy. If an engine cannot evaluate an image, return `availability=False` with a clear explanation.
5. **Data Governance**: Never alter or augment the 12 reference images in `data/storage/references/`. Derived outputs (`crops/`, `heatmaps/`, `reports/`) are runtime artifacts only.

---

## 2. Directory Structure & Domain Separation

```
backend/
├── app/
│   ├── ai/               # Computer vision, OCR, and multi-evidence engines
│   │   ├── certification/ # FSSAI / regulatory syntax validation
│   │   ├── codes/         # Barcode & QR decoders
│   │   ├── decision/      # Risk assessment & state evaluator
│   │   ├── detection/     # Bounding box & contour detector
│   │   ├── explainability/# Heatmap generator & explanation synthesizer
│   │   ├── fingerprint/   # Multi-modal packaging fingerprint generator
│   │   ├── fusion/        # Dempster-Shafer & weighted evidential fusion
│   │   ├── ocr/           # Text extraction & regex parser
│   │   ├── quality/       # Laplacian blur, glare, contrast evaluator
│   │   ├── reporting/     # ReportLab PDF certificate generator
│   │   ├── retrieval/     # Top-K candidate reference retriever
│   │   ├── vision/        # Logo, layout, colour, texture, seal, shape, print
│   │   ├── contracts.py   # Pydantic contracts & engine abstract base classes
│   │   └── orchestrator.py# Central AI pipeline orchestrator
│   ├── api/              # FastAPI routers (v1) and dependency injectors
│   ├── core/             # Configuration, database engines, security, storage
│   ├── models/           # SQLAlchemy ORM declarative models
│   ├── schemas/          # Pydantic request/response validation schemas
│   └── services/         # Application domain services
├── migrations/           # Alembic database migration revisions
├── scripts/              # Seed scripts and maintenance utilities
└── tests/                # Comprehensive pytest suite
```

---

## 3. How to Add a New Evidence Engine

To add a new evidence engine (e.g. `WatermarkAnalyzer` or `HologramAnalyzer`):

### Step 1: Define Interface Contract
In `backend/app/ai/contracts.py`, define the engine interface inheriting from `ABC`:
```python
class BaseWatermarkAnalyzer(ABC):
    @abstractmethod
    def analyze(
        self,
        crop_bgr: np.ndarray,
        ref_crop_bgr: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceObject:
        pass
```

### Step 2: Implement the Engine
Create `backend/app/ai/vision/watermark.py`:
```python
class WatermarkAnalyzer(BaseWatermarkAnalyzer):
    def analyze(self, crop_bgr, ref_crop_bgr=None, metadata=None) -> EvidenceObject:
        if ref_crop_bgr is None:
            return EvidenceObject(
                type=EvidenceType.PACKAGING,
                score=None,
                confidence=0.0,
                availability=False,
                quality=0.5,
                source="watermark-v1",
                explanation="No reference template available for watermark comparison."
            )
        # Real OpenCV / FFT analysis
        ...
```

### Step 3: Register in Orchestrator
In `backend/app/ai/orchestrator.py`:
1. Import `WatermarkAnalyzer`.
2. Instantiate in `AIOrchestrator.__init__`.
3. Invoke during Stage 5 and append to `evidences`.

### Step 4: Add Unit & Integration Tests
Add test assertions in `backend/tests/test_phase5_to_11_pipeline.py` verifying that the engine emits a valid `EvidenceObject` under normal, noisy, and missing-reference conditions.

---

## 4. Database Migrations (Alembic)

When modifying SQLAlchemy models in `backend/app/models/`:

```bash
# 1. Generate new migration script
python -m alembic revision --autogenerate -m "describe_change"

# 2. Inspect generated file in backend/migrations/versions/
# Verify table changes and batch_alter_table compatibility

# 3. Apply migration to database
python -m alembic upgrade head

# 4. Verify no pending schema diffs
python -m alembic check
```

---

## 5. Testing & Quality Assurance

```bash
# Run all backend tests with verbose output
python -m pytest backend/tests/ -v

# Run specific test module
python -m pytest backend/tests/test_phase1_models_and_db.py -v

# Run frontend build check (TypeScript & Vite)
cd frontend
npm run build
cd ..
```


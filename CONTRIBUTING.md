# Contributing to VeriSure AI

Thank you for your interest in contributing to VeriSure AI! This document outlines our code standards, branching model, and review requirements.

---

## 1. Code of Conduct & Core Rules

1. **Zero Hallucination Policy**: Never commit code that fabricates AI results, manufactures fake accuracy, or hardcodes confidence scores.
2. **Data Governance**: Never modify, resize, or delete the 12 reference images in `data/storage/references/`.
3. **No Magic Numbers**: Centralize thresholds in `backend/app/core/config.py`.
4. **Comprehensive Testing**: Any new feature or bug fix must include tests that pass via `pytest`.

---

## 2. Development Workflow

1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Set up local virtual environment and install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   cd frontend && npm install && cd ..
   ```
3. Make your changes adhering to PEP 8 and TypeScript strict mode.
4. Run backend tests:
   ```bash
   python -m pytest backend/tests/ -v
   ```
5. Run frontend build verification:
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
6. Commit with clear, conventional commit messages:
   ```bash
   git commit -m "feat(ai): add frequency edge clarity analyzer in print engine"
   ```
7. Open a Pull Request against `main`.

---

## 3. Pull Request Checklist

Before submitting a PR, verify:
* [ ] All 24+ backend tests pass cleanly.
* [ ] Frontend builds with 0 TypeScript errors and 0 warnings.
* [ ] Alembic migration added if database models were modified (`alembic check` passes).
* [ ] Documentation updated if API contracts or engine parameters changed.


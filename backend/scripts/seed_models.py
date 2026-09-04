import asyncio
from datetime import datetime
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.model_registry import EvaluationRun, ModelDeployment, ModelEntity, ModelVersionEntity


async def seed_initial_models():
    """
    Seeds initial production model registrations in the Model Registry.
    Scientific Integrity Rule: Evaluation metrics are set to None until an empirical
    physical benchmark dataset is collected and evaluated.
    """
    async with AsyncSessionLocal() as session:
        # 1. Multi-Evidence Fusion Model
        m1 = (await session.execute(select(ModelEntity).where(ModelEntity.name == "VeriSure Multi-Evidence Fusion Engine"))).scalar_one_or_none()
        if not m1:
            m1 = ModelEntity(
                name="VeriSure Multi-Evidence Fusion Engine",
                task="FUSION_VERIFICATION",
                architecture="Quality- and Certainty-Modulated Weighted Evidence Fusion with Multiplicative Contradiction Penalty",
                description="Core decision engine orchestrating 12 independent visual, textual, and machine-readable evidence models."
            )
            session.add(m1)
            await session.flush()

            v1 = ModelVersionEntity(
                model_id=m1.id,
                version_tag="v1.0.0",
                status="PRODUCTION",
                artifact_path="models/fusion_weights_v1.json",
                hyperparameters={
                    "base_weights": {
                        "logo": 0.18, "layout": 0.12, "colour": 0.10, "typography": 0.08,
                        "texture": 0.06, "shape": 0.08, "seal": 0.12, "print": 0.06,
                        "ocr": 0.10, "barcode": 0.05, "qr": 0.03, "certification": 0.02
                    },
                    "max_conflict_penalty": 0.45
                }
            )
            session.add(v1)
            await session.flush()

            eval1 = EvaluationRun(
                model_version_id=v1.id,
                accuracy=None,
                precision=None,
                recall=None,
                f1=None,
                roc_auc=None,
                confusion_matrix={
                    "status": "EMPIRICAL_DATASET_NOT_YET_AVAILABLE",
                    "message": "Empirical physical dataset not yet available. Physical product validation remains future work."
                },
                robustness_metrics={
                    "status": "PENDING_PHYSICAL_BENCHMARK",
                    "message": "Physical environmental robustness metrics require verified real-world retail captures."
                },
                evaluated_at=datetime.utcnow()
            )
            session.add(eval1)

            dep1 = ModelDeployment(
                model_version_id=v1.id,
                environment="PRODUCTION",
                deployed_at=datetime.utcnow(),
                is_active=True
            )
            session.add(dep1)

        # 2. Logo Keypoint Homography Verifier
        m2 = (await session.execute(select(ModelEntity).where(ModelEntity.name == "VeriSure Logo Keypoint Homography Verifier"))).scalar_one_or_none()
        if not m2:
            m2 = ModelEntity(
                name="VeriSure Logo Keypoint Homography Verifier",
                task="LOGO_VERIFICATION",
                architecture="ORB + RANSAC Homography + CIELAB Color Match",
                description="Localized logo detector and geometric invariant matching model."
            )
            session.add(m2)
            await session.flush()

            v2 = ModelVersionEntity(
                model_id=m2.id,
                version_tag="v1.0.0",
                status="PRODUCTION",
                artifact_path="models/logo_orb_params_v1.json",
                hyperparameters={"n_features": 500, "scale_factor": 1.2, "n_levels": 4}
            )
            session.add(v2)
            await session.flush()

            eval2 = EvaluationRun(
                model_version_id=v2.id,
                accuracy=None,
                precision=None,
                recall=None,
                f1=None,
                roc_auc=None,
                confusion_matrix={
                    "status": "EMPIRICAL_DATASET_NOT_YET_AVAILABLE",
                    "message": "Empirical physical dataset not yet available."
                },
                evaluated_at=datetime.utcnow()
            )
            session.add(eval2)

            dep2 = ModelDeployment(
                model_version_id=v2.id,
                environment="PRODUCTION",
                deployed_at=datetime.utcnow(),
                is_active=True
            )
            session.add(dep2)

        await session.commit()
        print("Model Registry successfully seeded with registered initial production models!")


if __name__ == "__main__":
    asyncio.run(seed_initial_models())

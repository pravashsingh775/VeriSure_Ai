from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.audit import log_audit_event
from backend.app.models.dataset import Dataset, DatasetSample, DatasetVersion
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetVersionCreate,
    DatasetVersionResponse,
)


class DatasetService:
    @staticmethod
    async def create_dataset(db: AsyncSession, data: DatasetCreate, actor_id: Optional[str] = None) -> DatasetResponse:
        dataset = Dataset(
            name=data.name,
            description=data.description,
            domain_tag=data.domain_tag
        )
        db.add(dataset)
        await db.flush()

        ds_id = dataset.id
        ds_created_at = dataset.created_at

        await log_audit_event(
            session=db,
            action="DATASET_CREATED",
            resource_type="DATASET",
            resource_id=ds_id,
            user_id=actor_id,
            changes={"name": dataset.name, "domain_tag": dataset.domain_tag}
        )
        await db.commit()
        return DatasetResponse(
            id=ds_id,
            name=data.name,
            description=data.description,
            domain_tag=data.domain_tag,
            versions=[],
            created_at=ds_created_at
        )

    @staticmethod
    async def list_datasets(db: AsyncSession) -> List[DatasetResponse]:
        stmt = select(Dataset).options(selectinload(Dataset.versions))
        result = await db.execute(stmt)
        datasets = result.scalars().all()
        return [DatasetResponse.model_validate(d) for d in datasets]

    @staticmethod
    async def create_version(
        db: AsyncSession,
        dataset_id: str,
        data: DatasetVersionCreate,
        actor_id: Optional[str] = None
    ) -> DatasetVersionResponse:
        # Check dataset exists
        dataset = (await db.execute(select(Dataset).where(Dataset.id == dataset_id))).scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

        train_count = sum(1 for s in data.samples if s.split == "TRAIN")
        val_count = sum(1 for s in data.samples if s.split == "VAL")
        test_count = sum(1 for s in data.samples if s.split == "TEST")

        version = DatasetVersion(
            dataset_id=dataset_id,
            version_tag=data.version_tag,
            split_strategy=data.split_strategy,
            train_count=train_count,
            val_count=val_count,
            test_count=test_count,
            is_locked=True,  # Versions are immutable snapshots
            metadata_json=data.metadata_json
        )
        db.add(version)
        await db.flush()

        for sample_data in data.samples:
            sample = DatasetSample(
                dataset_version_id=version.id,
                image_path=sample_data.image_path,
                label=sample_data.label,
                split=sample_data.split,
                package_id=sample_data.package_id,
                capture_session_id=sample_data.capture_session_id
            )
            db.add(sample)
            await db.flush()

        await log_audit_event(
            session=db,
            action="DATASET_VERSION_FROZEN",
            resource_type="DATASET_VERSION",
            resource_id=version.id,
            user_id=actor_id,
            changes={"version_tag": version.version_tag, "samples_total": len(data.samples)}
        )
        await db.commit()
        return DatasetVersionResponse.model_validate(version)

"""phase6_normalized_schema

Revision ID: 8e102de0cea4
Revises: 
Create Date: 2026-09-03 18:55:17.392258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e102de0cea4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    from backend.app.core.database import BaseModel
    import backend.app.models

    # 1. Ensure all normalized tables are created if starting on a clean database
    BaseModel.metadata.create_all(bind=bind)

    # 2. For existing database environments, apply schema alterations idempotently
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if 'feedback_samples' in table_names:
        cols = [c['name'] for c in inspector.get_columns('feedback_samples')]
        if 'origin_type' not in cols:
            with op.batch_alter_table('feedback_samples') as batch_op:
                batch_op.add_column(sa.Column('origin_type', sa.String(length=30), nullable=False, server_default='SCAN'))

    if 'product_pack_sizes' in table_names:
        pps_cols = [c['name'] for c in inspector.get_columns('product_pack_sizes')]
        if 'standard_mrp' in pps_cols:
            with op.batch_alter_table('product_pack_sizes') as batch_op:
                batch_op.drop_column('standard_mrp')

    if 'reports' in table_names:
        rep_cols = [c['name'] for c in inspector.get_columns('reports')]
        if 'pdf_sha256' not in rep_cols:
            with op.batch_alter_table('reports') as batch_op:
                batch_op.add_column(sa.Column('pdf_sha256', sa.String(length=64), nullable=True))

    if 'users' in table_names:
        user_cols = [c['name'] for c in inspector.get_columns('users')]
        if 'brand_id' in user_cols:
            with op.batch_alter_table('users') as batch_op:
                batch_op.drop_column('brand_id')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('brand_id', sa.String(length=36), nullable=True))

    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_column('pdf_sha256')

    with op.batch_alter_table('product_pack_sizes') as batch_op:
        batch_op.add_column(sa.Column('standard_mrp', sa.Float(), nullable=True))

    with op.batch_alter_table('feedback_samples') as batch_op:
        batch_op.drop_column('origin_type')

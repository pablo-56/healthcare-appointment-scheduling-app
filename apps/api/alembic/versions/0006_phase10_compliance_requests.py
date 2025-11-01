"""phase10: compliance_requests table

Revision ID: 0006_phase10_compliance_requests
Revises: 0005_p9_add_cols_ps
Create Date: 2025-10-30
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_phase10_compliance_requests"
down_revision = "p9_add_cols_ps"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "compliance_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False, index=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True, index=True),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("result_url", sa.String(length=1024), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # NOTE: no explicit op.create_index calls here — the index=True flags above are enough.


def downgrade():
    op.drop_table("compliance_requests")

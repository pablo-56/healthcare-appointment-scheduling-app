"""phase11: experiments + assignments tables

Revision ID: 0007_phase11_experiments
Revises: 0006_phase10_compliance_requests
Create Date: 2025-10-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007_phase11_experiments"
down_revision = "0006_phase10_compliance_requests"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("variants", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("name"),
    )
    #op.create_index("ix_experiments_name", "experiments", ["name"])

    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("experiments.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=True),
        sa.Column("variant", sa.String(length=32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
    )
    #op.create_index("ix_experiment_assignments_experiment", "experiment_assignments", ["experiment_id"])

def downgrade() -> None:
    op.drop_index("ix_experiment_assignments_experiment", table_name="experiment_assignments")
    op.drop_table("experiment_assignments")
    op.drop_index("ix_experiments_name", table_name="experiments")
    op.drop_table("experiments")

"""phase9: patient_surveys table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "phase9_patient_surveys"          # keep your current value
down_revision = "0003_phase3_eligibility"    # keep your current previous rev
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Create table only if missing
    existing_tables = set(insp.get_table_names())
    if "patient_surveys" not in existing_tables:
        op.create_table(
            "patient_surveys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
            sa.Column("instrument", sa.String(length=32), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )

    # 2) Create index only if missing
    #    (table must exist here)
    idx_names = {ix["name"] for ix in insp.get_indexes("patient_surveys")}
    if "ix_patient_surveys_instrument" not in idx_names:
        op.create_index("ix_patient_surveys_instrument", "patient_surveys", ["instrument"])


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop index if exists
    if "patient_surveys" in insp.get_table_names():
        existing = {ix["name"] for ix in insp.get_indexes("patient_surveys")}
        if "ix_patient_surveys_instrument" in existing:
            op.drop_index("ix_patient_surveys_instrument", table_name="patient_surveys")

    # Drop table if exists
    if "patient_surveys" in insp.get_table_names():
        op.drop_table("patient_surveys")

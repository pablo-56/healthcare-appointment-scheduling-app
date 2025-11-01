# alembic/versions/0005_p9_add_cols_ps.py
from alembic import op
import sqlalchemy as sa

# Keep revision <= 32 chars to fit your alembic_version column
revision = "p9_add_cols_ps"
down_revision = "phase9_add_appt"
branch_labels = None
depends_on = None

def _has_column(table, col):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    return col in cols

def _has_fk(table, fk_name):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(fk["name"] == fk_name for fk in insp.get_foreign_keys(table))

def upgrade():
    # Add missing columns safely
    with op.batch_alter_table("patient_surveys") as batch_op:
        if not _has_column("patient_surveys", "appointment_id"):
            batch_op.add_column(sa.Column("appointment_id", sa.Integer(), nullable=True))
        if not _has_column("patient_surveys", "encounter_id"):
            batch_op.add_column(sa.Column("encounter_id", sa.String(length=64), nullable=True))
        if not _has_column("patient_surveys", "language"):
            batch_op.add_column(sa.Column("language", sa.String(length=8), nullable=True, server_default="en"))

    # Create FK only if missing and column exists
    if _has_column("patient_surveys", "appointment_id") and not _has_fk("patient_surveys", "patient_surveys_appointment_id_fkey"):
        op.create_foreign_key(
            "patient_surveys_appointment_id_fkey",
            "patient_surveys",
            "appointments",
            ["appointment_id"],
            ["id"],
        )

    # Create indexes (Postgres) only if missing
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patient_surveys_appointment_id ON patient_surveys (appointment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patient_surveys_encounter_id ON patient_surveys (encounter_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patient_surveys_instrument ON patient_surveys (instrument)"
    )

def downgrade():
    # Best-effort, tolerant drops
    op.execute("DROP INDEX IF EXISTS ix_patient_surveys_appointment_id")
    op.execute("DROP INDEX IF EXISTS ix_patient_surveys_encounter_id")
    # instrument index may have pre-existed; skip dropping to be safe, or uncomment next line if you created it here:
    # op.execute("DROP INDEX IF EXISTS ix_patient_surveys_instrument")

    # Drop FK then columns (IF EXISTS for safety)
    op.execute(
        "ALTER TABLE patient_surveys DROP CONSTRAINT IF EXISTS patient_surveys_appointment_id_fkey"
    )
    op.execute(
        "ALTER TABLE patient_surveys DROP COLUMN IF EXISTS language"
    )
    op.execute(
        "ALTER TABLE patient_surveys DROP COLUMN IF EXISTS encounter_id"
    )
    op.execute(
        "ALTER TABLE patient_surveys DROP COLUMN IF EXISTS appointment_id"
    )

# alembic/versions/0005_phase9_add_appt_to_patient_surveys.py
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "phase9_add_appt"
down_revision = "phase9_patient_surveys"  # whatever your prev rev id is
branch_labels = None
depends_on = None

def upgrade():
    # Add column if missing (idempotent)
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='patient_surveys' AND column_name='appointment_id'
      ) THEN
        ALTER TABLE patient_surveys ADD COLUMN appointment_id integer;
      END IF;
    END$$;
    """)

    # Create index if missing
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_patient_surveys_appointment_id
    ON patient_surveys(appointment_id);
    """)

def downgrade():
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='patient_surveys' AND column_name='appointment_id'
      ) THEN
        ALTER TABLE patient_surveys DROP COLUMN appointment_id;
      END IF;
    END$$;
    """)

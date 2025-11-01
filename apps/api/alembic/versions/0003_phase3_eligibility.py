"""phase 3 - eligibility_responses table"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_phase3_eligibility"
down_revision = '0001_init'  # set this to your actual previous revision id
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "eligibility_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), nullable=False, index=True),
        sa.Column("eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("copay_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_eligibility_responses_appt", "eligibility_responses", ["appointment_id"])

def downgrade():
    op.drop_index("ix_eligibility_responses_appt", table_name="eligibility_responses")
    op.drop_table("eligibility_responses")

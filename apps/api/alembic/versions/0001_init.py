from alembic import op
import sqlalchemy as sa

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('patients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mrn', sa.String(length=64), nullable=True),
        sa.Column('first_name', sa.String(length=128), nullable=True),
        sa.Column('last_name', sa.String(length=128), nullable=True),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('email', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    op.create_index('ix_patients_mrn', 'patients', ['mrn'])
    op.create_index('ix_patients_phone', 'patients', ['phone'])
    op.create_index('ix_patients_email', 'patients', ['email'])

    op.create_table('appointments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id')),
        sa.Column('start_at', sa.DateTime(timezone=True)),
        sa.Column('end_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(length=32)),
        sa.Column('fhir_appointment_id', sa.String(length=128)),
        sa.Column('reason', sa.String(length=256)),
        sa.Column('source_channel', sa.String(length=64)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    op.create_index('ix_appt_status', 'appointments', ['status'])

    op.create_table('intake_forms',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id')),
        sa.Column('answers_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )

    op.create_table('consents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id')),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.Column('signer_name', sa.String(length=128), nullable=True),
        sa.Column('signer_ip', sa.String(length=64), nullable=True),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )

    op.create_table('documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id'), nullable=True),
        sa.Column('kind', sa.String(length=64)),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    op.create_index('ix_documents_kind', 'documents', ['kind'])

    op.create_table('tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('type', sa.String(length=64)),
        sa.Column('status', sa.String(length=32), default='open'),
        sa.Column('payload_json', sa.JSON(), nullable=True),
        sa.Column('assignee', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    op.create_index('ix_tasks_type', 'tasks', ['type'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])

    op.create_table('claims',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id')),
        sa.Column('status', sa.String(length=32), default='NEW'),
        sa.Column('payer_ref', sa.String(length=128), nullable=True),
        sa.Column('payload_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    op.create_index('ix_claims_status', 'claims', ['status'])

    op.create_table('policy_chunks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor', sa.String(length=128), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=True),
        sa.Column('target', sa.String(length=128), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    op.create_index('ix_audit_action_time', 'audit_logs', ['action', 'created_at'])

def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('policy_chunks')
    op.drop_index('ix_claims_status', table_name='claims')
    op.drop_table('claims')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_type', table_name='tasks')
    op.drop_table('tasks')
    op.drop_index('ix_documents_kind', table_name='documents')
    op.drop_table('documents')
    op.drop_table('consents')
    op.drop_table('intake_forms')
    op.drop_index('ix_appt_status', table_name='appointments')
    op.drop_table('appointments')
    op.drop_index('ix_patients_email', table_name='patients')
    op.drop_index('ix_patients_phone', table_name='patients')
    op.drop_index('ix_patients_mrn', table_name='patients')
    op.drop_table('patients')

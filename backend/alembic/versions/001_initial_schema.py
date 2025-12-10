"""Initial schema with all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-12-10 00:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (only if they don't exist)
    op.execute("""DO $$ BEGIN
        CREATE TYPE userrole AS ENUM ('user', 'admin', 'labeler', 'partner');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;""")
    
    op.execute("""DO $$ BEGIN
        CREATE TYPE capturestatus AS ENUM ('queued', 'processing', 'done', 'failed', 'edited');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;""")
    
    op.execute("""DO $$ BEGIN
        CREATE TYPE capturesource AS ENUM ('web', 'mobile');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;""")
    
    op.execute("""DO $$ BEGIN
        CREATE TYPE artifacttype AS ENUM ('aligned', 'mask', 'heatmap', 'raw');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;""")
    
    op.execute("""DO $$ BEGIN
        CREATE TYPE adjustmentsource AS ENUM ('user', 'tailor', 'admin');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;""")

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'admin', 'labeler', 'partner', name='userrole'), 
                  nullable=False, server_default='user'),
        sa.Column('consent_flags', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Create captures table
    op.create_table(
        'captures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('queued', 'processing', 'done', 'failed', 'edited', name='capturestatus'),
                  nullable=False, server_default='queued'),
        sa.Column('source', postgresql.ENUM('web', 'mobile', name='capturesource'), 
                  nullable=False, server_default='web'),
        sa.Column('store_images', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_captures_status', 'captures', ['status'])
    op.create_index('ix_captures_created_at', 'captures', ['created_at'])
    op.create_index('idx_user_status', 'captures', ['user_id', 'status'])

    # Create user_adjustments table (before capture_metrics due to FK)
    op.create_table(
        'user_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('capture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_metrics_json', postgresql.JSONB, nullable=False),
        sa.Column('adjusted_metrics_json', postgresql.JSONB, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('source', postgresql.ENUM('user', 'tailor', 'admin', name='adjustmentsource'),
                  nullable=False, server_default='user'),
        sa.Column('approved', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['capture_id'], ['captures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id']),
    )
    op.create_index('idx_capture_adjustments', 'user_adjustments', ['capture_id', 'created_at'])

    # Create capture_metrics table
    op.create_table(
        'capture_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('capture_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('metrics_json', postgresql.JSONB, nullable=False),
        sa.Column('skin_json', postgresql.JSONB, nullable=True),
        sa.Column('shape_json', postgresql.JSONB, nullable=True),
        sa.Column('quality_json', postgresql.JSONB, nullable=True),
        sa.Column('model_versions', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('latest_adjustment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['capture_id'], ['captures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['latest_adjustment_id'], ['user_adjustments.id']),
    )

    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('capture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bucket_path', sa.String(512), nullable=False),
        sa.Column('artifact_type', postgresql.ENUM('aligned', 'mask', 'heatmap', 'raw', name='artifacttype'), nullable=False),
        sa.Column('file_size_bytes', sa.Integer, nullable=True),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['capture_id'], ['captures.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_capture_artifact_type', 'artifacts', ['capture_id', 'artifact_type'])

    # Create labels table
    op.create_table(
        'labels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('capture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('labeler_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('measurements_json', postgresql.JSONB, nullable=False),
        sa.Column('approved', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['capture_id'], ['captures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['labeler_id'], ['users.id']),
    )
    op.create_index('ix_labels_capture_id', 'labels', ['capture_id'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_actor_action', 'audit_logs', ['actor_id', 'action'])
    op.create_index('idx_resource', 'audit_logs', ['resource_type', 'resource_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('labels')
    op.drop_table('artifacts')
    op.drop_table('capture_metrics')
    op.drop_table('user_adjustments')
    op.drop_table('captures')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE adjustmentsource')
    op.execute('DROP TYPE artifacttype')
    op.execute('DROP TYPE capturesource')
    op.execute('DROP TYPE capturestatus')
    op.execute('DROP TYPE userrole')

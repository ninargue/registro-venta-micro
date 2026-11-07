"""baseline

Revision ID: ba617f3a8caa
Revises:
Create Date: 2026-11-02 00:01:43.326315

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "ba617f3a8caa"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

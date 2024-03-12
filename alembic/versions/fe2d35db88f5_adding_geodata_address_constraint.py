"""adding geodata address constraint

Revision ID: fe2d35db88f5
Revises: fa55372562d1
Create Date: 2024-03-09 01:44:29.769677

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fe2d35db88f5"
down_revision: Union[str, None] = "fa55372562d1"
branch_labels: Union[str, Sequence[str], None] = (
    None
)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "geodatas",
        "address",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "geodatas",
        "address",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    # ### end Alembic commands ###
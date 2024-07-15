"""adding image_uuid field to cafe

Revision ID: af4a016e3474
Revises: d3d437bcd247
Create Date: 2024-05-11 12:59:43.439998

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "af4a016e3474"
down_revision: Union[str, None] = "d3d437bcd247"
branch_labels: Union[str, Sequence[str], None] = (
    None
)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "descriptions",
        sa.Column(
            "image_uuid",
            sa.String(),
            nullable=True,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("descriptions", "image_uuid")
    # ### end Alembic commands ###

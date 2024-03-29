"""added company name_ru

Revision ID: 2e7368ef7617
Revises: 262abe040913
Create Date: 2024-03-06 02:58:54.607508

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2e7368ef7617"
down_revision: Union[str, None] = "262abe040913"
branch_labels: Union[str, Sequence[str], None] = (
    None
)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "companies",
        sa.Column(
            "name_ru", sa.String(), nullable=True
        ),
    )
    op.create_unique_constraint(
        None, "companies", ["name_ru"]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        None, "companies", type_="unique"
    )
    op.drop_column("companies", "name_ru")
    # ### end Alembic commands ###

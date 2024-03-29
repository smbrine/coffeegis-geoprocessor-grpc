"""fixing relationships 6

Revision ID: 341d2b4cac43
Revises: 2fc0e68ce7e7
Create Date: 2024-03-05 23:58:41.696326

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "341d2b4cac43"
down_revision: Union[str, None] = "2fc0e68ce7e7"
branch_labels: Union[str, Sequence[str], None] = (
    None
)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "cities_country_id_fkey",
        "cities",
        type_="foreignkey",
    )
    op.drop_column("cities", "country_id")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "cities",
        sa.Column(
            "country_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "cities_country_id_fkey",
        "cities",
        "countries",
        ["country_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###

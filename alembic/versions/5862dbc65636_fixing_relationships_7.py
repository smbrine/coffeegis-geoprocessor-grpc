"""fixing relationships 7

Revision ID: 5862dbc65636
Revises: 341d2b4cac43
Create Date: 2024-03-06 00:07:25.660309

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5862dbc65636"
down_revision: Union[str, None] = "341d2b4cac43"
branch_labels: Union[str, Sequence[str], None] = (
    None
)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "cities",
        sa.Column(
            "country_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        None,
        "cities",
        "countries",
        ["country_id"],
        ["id"],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        None, "cities", type_="foreignkey"
    )
    op.drop_column("cities", "country_id")
    # ### end Alembic commands ###

"""adding roaster and description

Revision ID: 4b7db39b1f81
Revises: fe2d35db88f5
Create Date: 2024-03-20 20:16:39.672589

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4b7db39b1f81"
down_revision: Union[str, None] = "fe2d35db88f5"
branch_labels: Union[str, Sequence[str], None] = (
    None
)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "roasters",
        sa.Column(
            "name", sa.String(), nullable=False
        ),
        sa.Column(
            "website", sa.String(), nullable=True
        ),
        sa.Column(
            "id", sa.String(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "descriptions",
        sa.Column(
            "location_description",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "interior_description",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "menu_description",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "place_history",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "arbitrary_description",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "cafe_id", sa.String(), nullable=False
        ),
        sa.Column(
            "id", sa.String(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["cafe_id"],
            ["cafes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_table("reviews")
    op.add_column(
        "cafes",
        sa.Column(
            "roaster_id",
            sa.String(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        None,
        "cafes",
        "roasters",
        ["roaster_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        None, "cafes", type_="foreignkey"
    )
    op.drop_column("cafes", "roaster_id")
    op.create_table(
        "reviews",
        sa.Column(
            "rating",
            sa.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "author",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "cafe_id",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["cafe_id"],
            ["cafes.id"],
            name="reviews_cafe_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id", name="reviews_pkey"
        ),
    )
    op.drop_table("descriptions")
    op.drop_table("roasters")
    # ### end Alembic commands ###
from datetime import datetime
from uuid import uuid4

import sqlalchemy
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    and_,
    select,
)
from sqlalchemy.exc import (
    IntegrityError,
    NoResultFound,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    relationship,
    selectinload,
)


from db.main import Base


class BaseModel(Base):
    __abstract__ = True
    id = Column(String, primary_key=True)
    created_at = Column(
        DateTime, default=datetime.now
    )

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        identifier=None,
        created_at=None,
        **kwargs,
    ):
        if not identifier:
            identifier = str(uuid4())
        if not created_at:
            created_at = datetime.now()

        transaction = cls(
            id=identifier,
            created_at=created_at,
            **kwargs,
        )
        try:
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
        except IntegrityError as e:
            await db.rollback()
            raise RuntimeError(e) from e

        return transaction

    @classmethod
    async def get(
        cls, db: AsyncSession, identifier: str
    ):
        try:
            transaction = await db.get(
                cls, identifier
            )
        except NoResultFound:
            return None
        return transaction

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ):
        stmt = (
            select(cls).offset(skip).limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


class Company(BaseModel):
    __tablename__ = "companies"

    name = Column(String, unique=True)
    name_ru = Column(String, unique=True)

    description_ru = Column(
        String, default="Нет описания."
    )
    website = Column(String, default=None)

    cafes = relationship(
        "Cafe",
        back_populates="company",
        cascade="all, delete, delete-orphan",
        lazy="subquery",
    )

    def __repr__(self):
        return f"{self.name}"


class Cafe(BaseModel):
    __tablename__ = "cafes"

    company_id = Column(
        String,
        ForeignKey("companies.id"),
        nullable=False,
    )
    company = relationship(
        "Company",
        back_populates="cafes",
        lazy="joined",
    )

    geodata = relationship(
        "Geodata",
        back_populates="cafe",
        uselist=False,
        lazy="joined",
    )

    menu = relationship(
        "Menu",
        back_populates="cafe",
        uselist=False,
    )

    description = relationship(
        "Description",
        back_populates="cafe",
        uselist=False,
    )

    roasters = relationship(
        "Roaster", back_populates="receivers", uselist=True
    )


    @classmethod
    async def get_ids(cls, db: AsyncSession):
        stmt = select(cls.id)
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_full(
        cls,
        db: AsyncSession,
        cafe_id: str,
    ):
        stmt = (
            select(cls)
            .filter(cls.id == cafe_id)
            .options(
                selectinload(cls.company),
                selectinload(
                    cls.menu
                ).selectinload(Menu.entries),
                selectinload(cls.description),
                selectinload(cls.geodata),
                selectinload(cls.roaster),
            )
        )
        result = await db.execute(stmt)
        return result.scalar()

    def __repr__(self):
        try:
            return (
                f"{self.company.name_ru}: "
                f"{self.geodata.country.code}, "
                f"{self.geodata.city.code}: "
                f"{self.geodata.address[:40]}..."
            )
        except (
            sqlalchemy.orm.exc.DetachedInstanceError
        ):
            try:
                return f"{self.company.name_ru}"
            except (
                sqlalchemy.orm.exc.DetachedInstanceError
            ):
                return (
                    f"{self.geodata.country.code}, "
                    f"{self.geodata.city.code}: "
                    f"{self.geodata.address[:40]}..."
                )


class Geodata(BaseModel):
    __tablename__ = "geodatas"

    latitude = Column(
        Numeric(7, 4),
        nullable=False,
        unique=False,
    )
    longitude = Column(
        Numeric(7, 4),
        nullable=False,
        unique=False,
    )

    address = Column(
        String, nullable=False, unique=False
    )

    cafe = relationship(
        "Cafe", back_populates="geodata"
    )
    cafe_id = Column(
        String,
        ForeignKey(
            "cafes.id", ondelete="CASCADE"
        ),
        unique=True,
    )

    country = relationship(
        "Country",
        back_populates="geodata",
        lazy="joined",
    )
    country_id = Column(
        Integer,
        ForeignKey(
            "countries.id", ondelete="CASCADE"
        ),
    )

    city = relationship(
        "City",
        back_populates="geodata",
        lazy="joined",
    )
    city_id = Column(
        Integer,
        ForeignKey(
            "cities.id", ondelete="CASCADE"
        ),
    )

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        country: int = 0,
        city: int = 0,
        skip: int = 0,
        limit: int = 100,
    ):
        stmt = (
            select(cls)
            .filter(
                and_(
                    cls.country == country,
                    cls.city == city,
                )
            )
            .options(
                selectinload(
                    cls.cafe
                ).selectinload(Cafe.company),
                selectinload(cls.cafe)
                .selectinload(Cafe.menu)
                .selectinload(Menu.entries),
                selectinload(
                    cls.cafe
                ).selectinload(Cafe.geodata),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    def __repr__(self):
        try:
            return f"{self.country.name_ru}, {self.city.name_ru}, {self.address}"
        except (
            sqlalchemy.orm.exc.DetachedInstanceError
        ):
            return f"{self.address}"


class Roaster(BaseModel):
    __tablename__ = "roasters"
    name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    receivers = relationship(
        "Cafe", back_populates="roaster"
    )


class Description(BaseModel):
    __tablename__ = "descriptions"
    location_description = Column(
        String,
        nullable=True,
    )
    interior_description = Column(
        String,
        nullable=True,
    )
    menu_description = Column(
        String,
        nullable=True,
    )
    place_history = Column(
        String,
        nullable=True,
    )
    arbitrary_description = Column(
        String,
        nullable=True,
    )
    image_uuid = Column(String, nullable=True)
    cafe_id = Column(
        String,
        ForeignKey(
            "cafes.id", ondelete="CASCADE"
        ),
        nullable=False,
    )
    cafe = relationship(
        "Cafe",
        back_populates="description",
        lazy="joined",
    )

    def __repr__(self):
        text = str(
            self.location_description
            or self.interior_description
            or self.menu_description
            or self.place_history
            or self.arbitrary_description,
        )
        return (
            text if len(text) <= 70 else text[:69]
        )


class Menu(BaseModel):
    __tablename__ = "menus"

    cafe_id = Column(
        String,
        ForeignKey(
            "cafes.id", ondelete="CASCADE"
        ),
    )
    cafe = relationship(
        "Cafe",
        back_populates="menu",
        lazy="joined",
    )

    entries = relationship(
        "MenuEntry",
        back_populates="menu",
        cascade="all, delete, delete-orphan",
    )

    def __repr__(self):
        try:
            return f"Меню {self.cafe.company.name_ru or self.cafe.company.name}"
        except (
            sqlalchemy.orm.exc.DetachedInstanceError
        ):
            return f"Меню {self.id[:16]}..."


class MenuEntry(BaseModel):
    __tablename__ = "menu_entries"

    name = Column(String, unique=False)
    description_ru = Column(
        String, default="Нет описания."
    )
    price = Column(Float)

    menu = relationship(
        "Menu",
        back_populates="entries",
        lazy="joined",
    )
    menu_id = Column(
        String,
        ForeignKey(
            "menus.id", ondelete="CASCADE"
        ),
    )

    currency = relationship(
        "Currency",
        back_populates="entries",
        uselist=False,
    )
    currency_id = Column(
        Integer,
        ForeignKey(
            "currencies.id", ondelete="CASCADE"
        ),
    )

    def __repr__(self):
        return f"{self.name}"


class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True)
    code = Column(
        String, unique=True, nullable=False
    )
    name = Column(
        String, unique=True, nullable=False
    )
    name_ru = Column(
        String, unique=True, nullable=False
    )
    entries = relationship(
        "MenuEntry",
        back_populates="currency",
        lazy="noload",
    )

    def __repr__(self):
        return f"{self.name_ru} ({self.code})"


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)
    code = Column(
        String, unique=True, nullable=False
    )
    name = Column(
        String, unique=True, nullable=False
    )
    name_ru = Column(
        String, unique=True, nullable=False
    )

    geodata = relationship(
        "Geodata",
        back_populates="country",
        lazy="noload",
    )

    cities = relationship(
        "City", back_populates="country"
    )

    def __repr__(self):
        return f"{self.name_ru} ({self.code})"

    @classmethod
    async def get_cafes(
        cls,
        db: AsyncSession,
        country: str = "Russia",
        skip: int = 0,
        limit: int = 100,
    ):
        stmt = (
            select(
                Geodata.latitude,
                Geodata.longitude,
                Geodata.cafe_id,
            )
            .join(Geodata.country)
            .filter(Country.name == country)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.all()

    @classmethod
    async def get_all_cafes_regardless(
        cls,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ):
        stmt = (
            select(
                Geodata.latitude,
                Geodata.longitude,
                Geodata.cafe_id,
            )
            .join(Geodata.country)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.all()


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False)
    name = Column(
        String,
        unique=True,
        nullable=False,
    )
    name_ru = Column(
        String, unique=True, nullable=False
    )
    geodata = relationship(
        "Geodata", back_populates="city"
    )

    country_id = Column(
        Integer,
        ForeignKey("countries.id"),
        nullable=False,
    )
    country = relationship(
        "Country",
        back_populates="cities",
        uselist=False,
    )

    @classmethod
    async def get_cafes(
        cls,
        db: AsyncSession,
        city: str = "Moscow",
        skip: int = 0,
        limit: int = 100,
    ):
        stmt = (
            select(
                Geodata.latitude,
                Geodata.longitude,
                Geodata.cafe_id,
            )
            .join(Geodata.city)
            .filter(City.name == city)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return result.all()

    def __repr__(self):
        return (
            f"Город {self.name_ru} ({self.code})"
        )

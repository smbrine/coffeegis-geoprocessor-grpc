import math

import httpx


class CoordinatesProcessor:
    def __init__(self):
        pass

    @staticmethod
    async def _haversine(
        lat_a: float,
        lon_a: float,
        lat_b: float,
        lon_b: float,
    ):
        lon1, lat1, lon2, lat2 = map(
            math.radians,
            [lon_a, lat_a, lon_b, lat_b],
        )

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
        return c * r

    @classmethod
    async def coordinates_to_bbox(
        cls, latitude: float, longitude: float
    ):
        pass

    @classmethod
    async def coordinates_to_distance(
        cls,
        lat_a: float,
        lon_a: float,
        lat_b: float,
        lon_b: float,
        precision: int = None,
    ) -> float:
        d = await cls._haversine(
            lat_a, lon_a, lat_b, lon_b
        )
        if precision:
            d = round(d, precision)
        return d

    @classmethod
    async def address_to_coordinates(
        cls, address: str
    ):
        query = (
            f"https://geocode.arcgis.com/arcgis/rest/services/World/"
            f"GeocodeServer/find?f=json&text={address}"
        )
        async with httpx.AsyncClient() as client:
            r = await client.get(query)
        res = r.json()["locations"][0]["feature"][
            "geometry"
        ]
        return [
            round(res["y"], 4),
            round(res["x"], 4),
        ]

    @classmethod
    async def coordinates_to_address(
        cls, lat: float, lon: float
    ):
        query = (
            f"https://geocode.arcgis.com/arcgis/rest/services/World/"
            f"GeocodeServer/reverseGeocode?location={lon},{lat}&f=pjson"
        )
        async with httpx.AsyncClient() as client:
            r = await client.get(query)
        res = r.json()["address"]
        return res["Address"] or res["LongLabel"]


async def main():
    print(
        await CoordinatesProcessor.address_to_coordinates(
            "Moscow, Tverskaya, 1"
        )
    )
    print(
        await CoordinatesProcessor.coordinates_to_address(
            37.399746,
            55.895250,
        )
    )

    pass


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

import asyncio
import logging
from time import perf_counter_ns

import redis.asyncio as aioredis
from grpc import aio as grpc_aio
from grpc_reflection.v1alpha import reflection

from app import settings
from db import models
from db.main import sessionmanager
from geoutils import CoordinatesProcessor
from proto import (
    main_service_pb2,
    main_service_pb2_grpc,
)
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

logging.basicConfig(
    level=(
        logging.DEBUG
        if settings.DEBUG
        else logging.ERROR
    )
)

redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

es = AsyncElasticsearch(
    hosts=["http://localhost:9200"]
)

sessionmanager.init(settings.POSTGRES_URL)


async def fetch_cafe_ids_postgres(session):
    # Assuming `models.Cafe.get_ids(session)` fetches all cafe IDs from PostgreSQL
    return set(await models.Cafe.get_ids(session))


async def fetch_cafe_ids_elasticsearch():
    es_result = await es.search(
        index="cafes",
        body={
            "size": 1000,
            "_source": ["id"],
            "query": {"match_all": {}},
        },
    )
    return {
        hit["_source"]["id"]
        for hit in es_result["hits"]["hits"]
    }


async def sync_cafes_to_elasticsearch(session):
    postgres_cafe_ids, elasticsearch_cafe_ids = (
        await fetch_cafe_ids_postgres(session),
        await fetch_cafe_ids_elasticsearch(),
    )
    print(elasticsearch_cafe_ids)

    to_add_to_es = (
        postgres_cafe_ids - elasticsearch_cafe_ids
    )
    to_remove_from_es = (
        elasticsearch_cafe_ids - postgres_cafe_ids
    )

    await asyncio.gather(
        *[
            add_cafe_to_elasticsearch(
                session, cafe_id
            )
            for cafe_id in to_add_to_es
        ],
        *[
            delete_cafe_from_elasticsearch(
                cafe_id
            )
            for cafe_id in to_remove_from_es
        ],
    )

    print("Synchronization complete.")


async def add_cafe_to_elasticsearch(
    session, cafe_id
):
    cafe_data = await serialize_cafe_data(
        session, cafe_id
    )
    print(cafe_data)
    if cafe_data:
        await es.index(
            index="cafes",
            id=cafe_id,
            document=cafe_data,
        )


async def delete_cafe_from_elasticsearch(cafe_id):
    await es.delete(index="cafes", id=cafe_id)


async def serialize_cafe_data(session, cafe_id):
    cafe = await models.Cafe.get_full(
        session, cafe_id
    )
    if not cafe:
        return None

    return {
        "id": cafe_id,
        "name": cafe.company.name.lower(),
        "name_ru": cafe.company.name_ru.lower(),
        "address": cafe.geodata.address.lower(),
    }


async def serialize_cafe(
    cafe_model: models.Cafe, user_lat, user_lon
):
    distance = (
        await CoordinatesProcessor.coordinates_to_distance(
            user_lat,
            user_lon,
            cafe_model.geodata.latitude,
            cafe_model.geodata.longitude,
        )
        if user_lat and user_lon
        else 0
    )

    logging.debug(
        f"Calculated distance: {distance}"
    )

    cafe = {
        "name": cafe_model.company.name,
        "address": cafe_model.geodata.address,
        "distance": distance,
        "latitude": cafe_model.geodata.latitude,
        "longitude": cafe_model.geodata.longitude,
        "logo": cafe_model.company.logo,
        "review": (
            {
                "title": cafe_model.review.title,
                "body": cafe_model.review.body,
                "author": cafe_model.review.author,
                "rating": cafe_model.review.rating,
            }
            if cafe_model.review
            else {}
        ),
    }
    return cafe


class CafeServiceServicer(
    main_service_pb2_grpc.CityCafeServiceServicer
):

    async def ListCafesPerCity(
        self, request, context
    ):
        return_length = request.len or 10
        logging.info(
            "Starting ListCafesPerCity method."
        )
        try:

            response = (
                main_service_pb2.ListCafesPerCityResponse()
            )
            async with sessionmanager.session() as session:
                city = request.city or "Moscow"
                logging.info(
                    f"Fetching cafes for city: {city}"
                )
                cafes_data = (
                    await models.City.get_cafes(
                        session, city
                    )
                )
                logging.debug(
                    f"Queried Cafes Data: {cafes_data}"
                )

                user_lat = request.latitude
                user_lon = request.longitude

                distances = []
                for cafe in cafes_data:
                    lat, lon, cafe_id = cafe
                    distance = await CoordinatesProcessor.coordinates_to_distance(
                        user_lat,
                        user_lon,
                        lat,
                        lon,
                    )
                    distances.append(
                        (distance, cafe_id)
                    )

                distances.sort(key=lambda x: x[0])
                closest_cafe_ids = [
                    cafe_id
                    for _, cafe_id in distances[
                        :return_length
                    ]
                ]

                closest_cafes = [
                    await models.Cafe.get_full(
                        session, cafe_id
                    )
                    for cafe_id in closest_cafe_ids
                ]
                logging.debug(
                    f"Queried Cafes: {closest_cafes}"
                )
            logging.info(
                "Successfully created ListCafesPerCityResponse."
            )

            for cafe in closest_cafes:
                cafe = await serialize_cafe(
                    cafe,
                    request.latitude,
                    request.longitude,
                )
                review = cafe.get("review", {})
                cafe_obj = main_service_pb2.Cafe(
                    name=cafe.get("name"),
                    address=cafe.get("address"),
                    distance=cafe.get("distance"),
                    latitude=cafe.get("latitude"),
                    longitude=cafe.get("longitude"),
                    review=(
                        main_service_pb2.Review(
                            title=review.get(
                                "title", ""
                            ),
                            body=review.get(
                                "body", ""
                            ),
                            author=review.get(
                                "author", ""
                            ),
                            rating=review.get(
                                "rating"
                            ),
                        )
                        if review
                        else None
                    ),
                )
                response.cafes.append(cafe_obj)
            return response
        except Exception as e:
            logging.error(
                f"An error occurred in ListCafesPerCity: {e}"
            )
            raise

    async def SearchCafesByQueryPerCity(
        self, request, context
    ):
        search_query = request.query
        city = request.city or "Moscow"
        limit = request.len or 10

        logging.info(
            f"Searching cafes for query: {search_query} in city: {city}"
        )

        try:
            # Query Elasticsearch for cafes in the specified city that match the search query
            tokens = search_query.lower().split(
                " "
            )
            clauses = [
                {
                    "multi_match": {
                        "query": token,
                        "fields": [
                            "name_ru",
                            "name",
                            "address",
                        ],
                        "fuzziness": "AUTO",
                    }
                }
                for token in tokens
            ]
            payload = {"bool": {"must": clauses}}
            print(payload)
            es_response = await es.search(
                index="cafes",
                query=payload,
                size=limit,
            )

            hits = es_response["hits"]["hits"]
            print(es_response)
            cafe_ids = [
                hit["_source"]["id"]
                for hit in hits
            ]

            if not cafe_ids:
                return (
                    main_service_pb2.SearchCafesByQueryPerCityResponse()
                )

            # Fetch full cafe details from PostgreSQL using the cafe IDs
            async with sessionmanager.session() as session:
                closest_cafes = [
                    await models.Cafe.get_full(
                        session, cafe_id
                    )
                    for cafe_id in cafe_ids
                ]
                logging.debug(
                    f"Queried Cafes: {closest_cafes}"
                )

            # Serialize the cafe details into the protobuf response
            response = (
                main_service_pb2.SearchCafesByQueryPerCityResponse()
            )
            for cafe in closest_cafes:
                cafe_obj = await serialize_cafe(
                    cafe,
                    request.latitude,
                    request.longitude,
                )  # Implement this function based on your protobuf structure
                response.cafes.append(
                    main_service_pb2.Cafe(
                        **cafe_obj
                    )
                )

            return response

        except Exception as e:
            logging.error(
                f"An error occurred in SearchCafesByQueryPerCity: {e}"
            )
            raise

    async def GetCafeDetails(
        self, request, context
    ):
        pass


async def serve():
    async with sessionmanager.session() as session:
        await sync_cafes_to_elasticsearch(
            session
        )
    server = grpc_aio.server()
    main_service_pb2_grpc.add_CityCafeServiceServicer_to_server(
        CafeServiceServicer(), server
    )

    listen_addr = "[::]:50051"
    service_names = (
        main_service_pb2.DESCRIPTOR.services_by_name[
            "CityCafeService"
        ].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(
        service_names, server
    )

    server.add_insecure_port(listen_addr)
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(0)


if __name__ == "__main__":
    asyncio.run(serve())

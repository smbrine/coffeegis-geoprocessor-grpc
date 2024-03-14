import asyncio
import json
import logging
import re
from decimal import Decimal
from time import perf_counter_ns
from typing import List

import redis.asyncio as aioredis
from grpc import aio as grpc_aio
from grpc_reflection.v1alpha import reflection
from sqlalchemy import Row

from app import settings
from db import models
from db.main import sessionmanager
from geoutils import CoordinatesProcessor
from proto import (
    main_service_pb2,
    main_service_pb2_grpc,
)
import pickle
from elasticsearch import AsyncElasticsearch
import elasticsearch


logging.basicConfig(
    level=(
        logging.DEBUG
        if settings.DEBUG
        else logging.ERROR
    )
)

redis = aioredis.from_url(
    settings.REDIS_URL,
    # encoding="utf-8",
    # decode_responses=True,
)

es = AsyncElasticsearch(
    hosts=["http://localhost:9200"]
)

sessionmanager.init(settings.POSTGRES_URL)


async def clean_string(input_string):
    # Use a regular expression to replace non-letter and non-digit characters with a space
    cleaned_string = re.sub(
        r"[^a-zA-Zа-яА-Я\d\- ]", "", input_string
    )
    # Convert to lowercase for uniformity
    cleaned_string = cleaned_string.lower()
    return cleaned_string


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


async def sync_cafes_to_elasticsearch(
    session_factory,
):
    # Using session_factory to manage sessions within subtasks
    async with session_factory() as session:
        postgres_cafe_ids = (
            await fetch_cafe_ids_postgres(session)
        )
        elasticsearch_cafe_ids = (
            await fetch_cafe_ids_elasticsearch()
        )

    to_add_to_es = (
        postgres_cafe_ids - elasticsearch_cafe_ids
    )
    to_remove_from_es = (
        elasticsearch_cafe_ids - postgres_cafe_ids
    )
    await asyncio.gather(
        *[
            add_cafe_to_elasticsearch(
                session_factory, cafe_id
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
    session_factory, cafe_id
):
    async with session_factory() as session:
        cafe_data = await serialize_cafe_data(
            session, cafe_id
        )
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
    res = {
        "id": cafe_id,
        "name": await clean_string(
            cafe.company.name
        ),
        "name_ru": await clean_string(
            cafe.company.name_ru
        ),
        "address": await clean_string(
            cafe.geodata.address
        ),
    }
    print(res)
    return res


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


async def fetch_cafe_details(
    cafe_id: str, session_factory, r=None
) -> dict:
    # Create a new session for this task
    async with session_factory() as session:
        # Your existing logic to fetch cafe details
        cache_key = f"cafes:full:{cafe_id}"
        if redis:
            if details_bytes := await r.get(
                cache_key
            ):
                return pickle.loads(details_bytes)
        cafe_details = await models.Cafe.get_full(
            session, cafe_id
        )
        if redis:
            await r.set(
                cache_key,
                pickle.dumps(cafe_details),
                180,
            )
        return cafe_details


async def fetch_multiple_cafes(
    cafe_ids: List[str], session_factory, r=None
):
    closest_cafes = await asyncio.gather(
        *[
            fetch_cafe_details(
                cafe_id, session_factory, r
            )
            for cafe_id in cafe_ids
        ]
    )
    return closest_cafes


class CafeServiceServicer(
    main_service_pb2_grpc.CityCafeServiceServicer
):

    async def ListCafesPerCity(
        self,  # I sincerely apologise for this function which is filled with antipatterns.
        request,  # I have appended it with different logics many times and at this moment
        context,  # I don't have enough time to completely rewrite it.
    ):
        return_length = request.len or 10
        logging.info(
            "Starting ListCafesPerCity method."
        )
        try:
            response = (
                main_service_pb2.ListCafesPerCityResponse()
            )
            global_cache_key = f"cafes:general:{request.city},{round(request.latitude,3)},{round(request.longitude,3)}"
            if response_bytes := await redis.get(
                global_cache_key
            ):
                return pickle.loads(
                    response_bytes
                )
            async with sessionmanager.session() as session:
                city = request.city or "Moscow"
                logging.info(
                    f"Fetching cafes for city: {city}"
                )

                city_cache_key = f"cafes:general:{request.city}"
                if cafes_bytes := await redis.get(
                    city_cache_key,
                ):
                    cafes_data = pickle.loads(
                        cafes_bytes,
                    )
                else:
                    cafes_data = await models.City.get_cafes(
                        session, city
                    )
                    await redis.set(
                        city_cache_key,
                        pickle.dumps(cafes_data),
                        300,
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
                closest_cafes = []
                for cafe_id in closest_cafe_ids:
                    full_cache_key = (
                        f"cafes:full:{cafe_id}"
                    )

                    if cafe_bytes := await redis.get(
                        full_cache_key
                    ):
                        closest_cafes.append(
                            pickle.loads(
                                cafe_bytes
                            )
                        )
                        continue

                    res = await models.Cafe.get_full(
                        session, cafe_id
                    )

                    await redis.set(
                        full_cache_key,
                        pickle.dumps(res),
                        270,
                    )
                    closest_cafes.append(res)

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
                    longitude=cafe.get(
                        "longitude"
                    ),
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

            await redis.set(
                global_cache_key,
                pickle.dumps(response),
                120,
            )
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
        global_cache_key = (
            f"cafes:query:{search_query},{city}"
        )
        if resp_bytes := await redis.get(
            global_cache_key
        ):
            return pickle.loads(resp_bytes)

        try:
            tokens = (
                await clean_string(search_query)
            ).split(" ")
            clauses = []
            for token in tokens:
                for field in [
                    "name",
                    "name_ru",
                    "address",
                ]:
                    clauses.append(
                        {
                            "match": {
                                field: {
                                    "query": token,
                                    "fuzziness": "AUTO",
                                }
                            }
                        }
                    )
                    wildcard_token = f"*{token}*"
                    clauses.append(
                        {
                            "wildcard": {
                                "address": {
                                    "value": wildcard_token
                                }
                            }
                        }
                    )

            payload = {
                "bool": {
                    "should": clauses,
                    "minimum_should_match": 1,
                }
            }
            print(payload)
            es_response = await es.search(
                index="cafes",
                query=payload,
                size=limit,
            )

            hits = es_response["hits"]["hits"]
            cafe_ids = [
                hit["_source"]["id"]
                for hit in hits
            ]

            if not cafe_ids:
                return (
                    main_service_pb2.SearchCafesByQueryPerCityResponse()
                )

            closest_cafes = (
                await fetch_multiple_cafes(
                    cafe_ids,
                    sessionmanager.session,
                    redis,
                )
            )
            logging.debug(
                f"Queried Cafes: {closest_cafes}"
            )

            response = (
                main_service_pb2.SearchCafesByQueryPerCityResponse()
            )
            for cafe in closest_cafes:
                cafe_obj = await serialize_cafe(
                    cafe,
                    request.latitude,
                    request.longitude,
                )
                response.cafes.append(
                    main_service_pb2.Cafe(
                        **cafe_obj
                    )
                )

            await redis.set(
                global_cache_key,
                pickle.dumps(response),
                180,
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
    try:
        await es.delete_by_query(
            index="cafes", query={"match_all": {}}
        )
    except elasticsearch.NotFoundError:
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
            },
            "mappings": {
                "properties": {
                    "name": {"type": "text"},
                    "name_ru": {"type": "text"},
                    "address": {"type": "text"},
                    "id": {"type": "text"},
                }
            },
        }
        await es.indices.create(
            index="cafes", body=index_body
        )

    await sync_cafes_to_elasticsearch(
        sessionmanager.session
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

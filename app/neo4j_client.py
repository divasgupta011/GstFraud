# app/neo4j_client.py
from neo4j import GraphDatabase, Driver
from functools import lru_cache

from .config import get_settings

@lru_cache
def get_neo4j_driver() -> Driver:
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(
            settings.neo4j_user,
            settings.neo4j_password,
        ),
    )
    return driver

def get_neo4j_session():
    driver = get_neo4j_driver()
    return driver.session()

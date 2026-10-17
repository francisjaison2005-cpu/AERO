"""Database configuration and connection management for AirPurify AI using MongoDB Atlas."""

import os
import logging
from typing import Generator, Optional
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database

# Load environment variables
load_dotenv()

logger = logging.getLogger("airpurify.database")

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://francisjaison2005_db_user:VKi8KDDqGchXfDKS@cluster0.9tdvmma.mongodb.net/?retryWrites=true&w=majority",
)
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "airpurify_db")

_mongo_client: Optional[MongoClient] = None


class _DummyMetadata:
    @staticmethod
    def create_all(*args, **kwargs):
        pass

    @staticmethod
    def drop_all(*args, **kwargs):
        pass


class Base:
    metadata = _DummyMetadata()


def get_mongo_client() -> MongoClient:
    """Return singleton MongoClient with connection pooling and timeouts."""
    global _mongo_client
    if _mongo_client is None:
        uri = os.getenv("MONGODB_URI", MONGODB_URI)
        _mongo_client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            retryWrites=True,
        )
    return _mongo_client


def get_mongo_db(db_name: Optional[str] = None) -> Database:
    """Return MongoDB Database instance."""
    client = get_mongo_client()
    target_name = db_name or os.getenv("MONGODB_DB_NAME", MONGODB_DB_NAME)
    return client[target_name]


def get_db() -> Generator[Database, None, None]:
    """Dependency that provides a MongoDB Database instance to route handlers.

    Yields:
        Database: Active MongoDB database instance.
    """
    db = get_mongo_db()
    yield db


def get_next_sequence_value(db: Database, sequence_name: str) -> int:
    """Generate atomic, auto-increment integer ID for collections.

    Ensures 100% backwards-compatibility with REST API contracts expecting integer IDs.
    """
    counter = db["counters"].find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return counter["seq"]


def check_mongo_health() -> bool:
    """Perform health-check ping to MongoDB Atlas."""
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        return True
    except Exception as exc:
        logger.error("MongoDB Atlas health-check ping failed: %s", exc)
        return False


def init_db(db_name: Optional[str] = None) -> None:
    """Initialize collections, indexes, and sequence counters on startup."""
    try:
        db = get_mongo_db(db_name)

        # Indexing devices
        db["devices"].create_index([("device_id", ASCENDING)], unique=True)
        db["devices"].create_index([("id", ASCENDING)], unique=True)
        db["devices"].create_index([("location_id", ASCENDING)])
        db["devices"].create_index([("status", ASCENDING)])

        # Indexing sensor readings
        db["sensor_readings"].create_index([("device_id", ASCENDING), ("timestamp", DESCENDING)])
        db["sensor_readings"].create_index([("location_id", ASCENDING), ("timestamp", DESCENDING)])
        db["sensor_readings"].create_index([("timestamp", DESCENDING)])
        db["sensor_readings"].create_index([("id", ASCENDING)], unique=True)

        # Indexing alerts
        db["alerts"].create_index([("device_id", ASCENDING), ("alert_type", ASCENDING), ("status", ASCENDING)])
        db["alerts"].create_index([("triggered_at", DESCENDING)])
        db["alerts"].create_index([("id", ASCENDING)], unique=True)

        # Indexing forecasts
        db["forecasts"].create_index([("location_id", ASCENDING), ("target_time", ASCENDING)])
        db["forecasts"].create_index([("id", ASCENDING)], unique=True)

        logger.info("MongoDB Atlas indexes verified on database '%s'.", db.name)
    except Exception as exc:
        logger.error("Failed to initialize MongoDB indexes: %s", exc)

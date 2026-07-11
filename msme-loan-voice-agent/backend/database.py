"""MongoDB helpers for storing call records."""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Defaults
DEFAULT_MONGO_URI = "mongodb://localhost:27017/msme_agent"
DB_NAME = "msme_agent"
COLLECTION_NAME = "calls"

_client: Optional[MongoClient] = None


def get_collection():
    """Get the calls collection from MongoDB."""
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
        _client = MongoClient(mongo_uri)
    db = _client.get_database()  # Uses the DB name from the URI
    return db[COLLECTION_NAME]


def init_db() -> None:
    """Initialize database indexes."""
    try:
        coll = get_collection()
        coll.create_index("call_id", unique=True)
        coll.create_index([("timestamp", -1)])
    except ConnectionFailure:
        # Ignore connect errors during initial startup sequence
        pass


def insert_call(record: Dict[str, Any]) -> None:
    """Insert or update a call record into the MongoDB collection."""
    coll = get_collection()
    call_id = record.get("call_id")
    
    # Insert or update based on call_id
    if call_id:
        coll.update_one(
            {"call_id": call_id},
            {"$set": record},
            upsert=True
        )
    else:
        # If no call_id for some reason, just insert it as a new record
        coll.insert_one(record)


def fetch_calls(limit: int = 0) -> List[Dict[str, Any]]:
    """Fetch all call records, sorted by timestamp descending."""
    coll = get_collection()
    cursor = coll.find({}).sort("timestamp", -1)
    if limit > 0:
        cursor = cursor.limit(limit)
    return list(cursor)


def fetch_call_by_id(call_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single call record by its call_id."""
    coll = get_collection()
    return coll.find_one({"call_id": call_id})

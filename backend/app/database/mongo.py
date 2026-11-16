from pymongo import MongoClient
import gridfs
from app.core.config import settings

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    return get_client()[settings.mongodb_db]


def get_gridfs():
    return gridfs.GridFS(get_db())


def ping() -> bool:
    if not settings.mongodb_uri:
        return False
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False

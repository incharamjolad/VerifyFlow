from pymongo import MongoClient
from app.core.config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    return get_client()[settings.mongodb_db]


def ping() -> bool:
    if not settings.mongodb_uri:
        return False
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False

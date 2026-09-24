from datetime import datetime

from pydantic import BaseModel

from backend.api import schemas
from backend.storage.database import get_db_path, init_db
from backend.storage.repositories.conversation.notification import NotificationRepository


def test_pydantic_models_do_not_declare_mutable_defaults():
    violations: list[str] = []
    for model_name, candidate in vars(schemas).items():
        if not isinstance(candidate, type) or not issubclass(candidate, BaseModel):
            continue
        if candidate.__module__ != schemas.__name__:
            continue
        for field_name, field in candidate.model_fields.items():
            if isinstance(field.default, (dict, list, set)):
                violations.append(f"{model_name}.{field_name}")

    assert violations == []


def test_notification_default_timestamp_is_utc_aware():
    db_path = str(get_db_path("data/aaa_timestamp_test.db"))
    init_db(db_path).close()
    notification = NotificationRepository(db_path).create(type="test", snippet="timestamp")

    timestamp = datetime.fromisoformat(notification["timestamp"])

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() is not None

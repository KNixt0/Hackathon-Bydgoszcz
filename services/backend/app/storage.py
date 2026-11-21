"""Evidence archive: S3-compatible object storage with automatic fallback to a Postgres table."""

from __future__ import annotations

import logging
import re
import time
from typing import Protocol

from app.config import Settings, get_settings
from app.db import session_scope
from app.models import Blob

log = logging.getLogger(__name__)

KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")


def valid_key(key: str) -> bool:
    return bool(KEY_RE.match(key)) and ".." not in key and "//" not in key


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> tuple[bytes, str] | None: ...
    def healthy(self) -> bool: ...


class DbStore:
    """Blobs in the `blobs` table."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        with session_scope() as db:
            db.merge(Blob(key=key, content_type=content_type, data=data))

    def get(self, key: str) -> tuple[bytes, str] | None:
        with session_scope() as db:
            blob = db.get(Blob, key)
            return (bytes(blob.data), blob.content_type) if blob else None

    def healthy(self) -> bool:
        try:
            with session_scope() as db:
                db.get(Blob, "-")
            return True
        except Exception:  # noqa: BLE001
            return False


class S3Store:
    def __init__(self, settings: Settings) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            region_name=settings.s3_region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=3,
                read_timeout=10,
                retries={"max_attempts": 1},
            ),
        )
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:  # noqa: BLE001
            self._client.create_bucket(Bucket=self.bucket)
        self._bucket_ready = True

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> tuple[bytes, str] | None:
        from botocore.exceptions import ClientError

        try:
            obj = self._client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NoSuchBucket"):
                return None
            raise
        return obj["Body"].read(), obj.get("ContentType") or "application/octet-stream"

    def healthy(self) -> bool:
        try:
            self._ensure_bucket()
            return True
        except Exception:  # noqa: BLE001
            self._bucket_ready = False
            return False


class FallbackStore:
    """Try the primary (S3); on any failure use the secondary (DB) and back off from S3 for a while."""

    def __init__(self, primary: ObjectStore | None, secondary: ObjectStore, cooldown: float = 60.0) -> None:
        self.primary = primary
        self.secondary = secondary
        self.cooldown = cooldown
        self._down_until = 0.0

    def _primary_up(self) -> bool:
        return self.primary is not None and time.monotonic() >= self._down_until

    def _mark_down(self, exc: Exception) -> None:
        self._down_until = time.monotonic() + self.cooldown
        log.warning(
            "object storage unreachable, using database fallback", extra={"error": type(exc).__name__}
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        if self._primary_up():
            try:
                self.primary.put(key, data, content_type)  # type: ignore[union-attr]
                return
            except Exception as exc:  # noqa: BLE001
                self._mark_down(exc)
        self.secondary.put(key, data, content_type)

    def get(self, key: str) -> tuple[bytes, str] | None:
        if self._primary_up():
            try:
                found = self.primary.get(key)  # type: ignore[union-attr]
                if found is not None:
                    return found
            except Exception as exc:  # noqa: BLE001
                self._mark_down(exc)
        return self.secondary.get(key)

    def backend(self) -> str:
        if self.primary is not None and self._primary_up() and self.primary.healthy():
            return "s3"
        return "db"

    def healthy(self) -> bool:
        return self.backend() == "s3" or self.secondary.healthy()


_store: ObjectStore | None = None


def get_store() -> ObjectStore:
    global _store
    if _store is None:
        settings = get_settings()
        primary: ObjectStore | None = None
        if settings.s3_endpoint:
            try:
                primary = S3Store(settings)
            except Exception as exc:  # noqa: BLE001
                log.warning("S3 client could not be created", extra={"error": type(exc).__name__})
        _store = FallbackStore(primary, DbStore())
    return _store


def set_store(store: ObjectStore | None) -> None:
    global _store
    _store = store

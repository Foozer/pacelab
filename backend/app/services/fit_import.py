"""Persist FIT uploads as provider='fit' activities.

Original FIT bytes are not stored. Identity is the session user, never a
client-supplied user_id. Re-uploading the same run updates the existing row.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.fit.parser import (
    FIT_PROVIDER,
    FitParseError,
    parse_fit_activity,
)
from app.models.activity import Activity
from app.services.activities import (
    activity_from_provider,
    apply_provider_summary,
    replace_provider_samples,
)
from app.services.activity_sync import record_provider_sync

logger = logging.getLogger(__name__)

MAX_FIT_FILES_PER_REQUEST = 20
MAX_FIT_FILE_BYTES = 8 * 1024 * 1024
_ALLOWED_SUFFIXES = (".fit", ".fit.gz")
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "",
        "application/octet-stream",
        "application/fit",
        "application/vnd.ant.fit",
        "application/gzip",
        "application/x-gzip",
        "application/fit+gzip",
    }
)


@dataclass(frozen=True, slots=True)
class FitFileOutcome:
    filename: str
    status: str
    activity_id: uuid.UUID | None = None
    provider_activity_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class FitImportResult:
    created: int
    updated: int
    skipped: int
    failed: int
    files: list[FitFileOutcome]
    last_sync_at: datetime | None


def validate_fit_upload(*, filename: str, content_type: str | None, size: int) -> None:
    name = filename.strip() if filename else ""
    lowered = name.lower()
    if not lowered.endswith(_ALLOWED_SUFFIXES):
        raise FitParseError(
            "UNSUPPORTED_FIT_FILE",
            "Upload a .fit or .fit.gz file exported from your watch or Garmin Connect.",
        )
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in _ALLOWED_CONTENT_TYPES:
        raise FitParseError(
            "UNSUPPORTED_FIT_FILE",
            "That file type is not a FIT upload.",
        )
    if size <= 0:
        raise FitParseError("EMPTY_FIT_FILE", "The FIT file was empty.")
    if size > MAX_FIT_FILE_BYTES:
        raise FitParseError(
            "FIT_FILE_TOO_LARGE",
            f"Each FIT file must be at most {MAX_FIT_FILE_BYTES // (1024 * 1024)} MB.",
        )


async def import_fit_files(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    uploads: list[tuple[str, str | None, bytes]],
) -> FitImportResult:
    """Import one or more FIT payloads for ``user_id``.

    ``uploads`` is (filename, content_type, bytes). Bytes stay in memory.
    """
    if len(uploads) > MAX_FIT_FILES_PER_REQUEST:
        raise FitParseError(
            "TOO_MANY_FIT_FILES",
            f"Upload at most {MAX_FIT_FILES_PER_REQUEST} FIT files at a time.",
        )
    if not uploads:
        raise FitParseError("EMPTY_FIT_FILE", "Choose at least one FIT file.")

    existing_rows = await session.execute(
        select(Activity)
        .options(selectinload(Activity.samples))
        .where(Activity.user_id == user_id, Activity.provider == FIT_PROVIDER)
    )
    by_provider_id = {row.provider_activity_id: row for row in existing_rows.scalars().all()}

    outcomes: list[FitFileOutcome] = []
    created = 0
    updated = 0
    skipped = 0
    failed = 0
    imported_any = False

    for filename, content_type, payload in uploads:
        try:
            validate_fit_upload(
                filename=filename,
                content_type=content_type,
                size=len(payload),
            )
            incoming = parse_fit_activity(payload)
            existing = by_provider_id.get(incoming.provider_activity_id)
            if existing is None:
                activity = activity_from_provider(user_id=user_id, incoming=incoming)
                session.add(activity)
                await session.flush()
                by_provider_id[incoming.provider_activity_id] = activity
                created += 1
                imported_any = True
                outcomes.append(
                    FitFileOutcome(
                        filename=filename,
                        status="created",
                        activity_id=activity.id,
                        provider_activity_id=incoming.provider_activity_id,
                    )
                )
            else:
                apply_provider_summary(existing, incoming)
                await replace_provider_samples(session, existing, incoming)
                updated += 1
                imported_any = True
                outcomes.append(
                    FitFileOutcome(
                        filename=filename,
                        status="updated",
                        activity_id=existing.id,
                        provider_activity_id=incoming.provider_activity_id,
                    )
                )
        except FitParseError as exc:
            failed += 1
            outcomes.append(
                FitFileOutcome(
                    filename=filename,
                    status="failed",
                    error_code=exc.code,
                    error_message=exc.message,
                )
            )

    last_sync_at = None
    if imported_any:
        last_sync_at = await record_provider_sync(
            session,
            user_id=user_id,
            provider_name=FIT_PROVIDER,
        )
        await session.flush()
        logger.info(
            "FIT import for user %s: created=%s updated=%s failed=%s files=%s",
            user_id,
            created,
            updated,
            failed,
            len(uploads),
        )

    return FitImportResult(
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        files=outcomes,
        last_sync_at=last_sync_at,
    )

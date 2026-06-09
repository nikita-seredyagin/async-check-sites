import asyncio
import time

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Check, Site
from app.schemas import CheckResponseSchema, RunChecksResponseSchema

router = APIRouter(prefix="/checks", tags=["checks"])

REQUEST_TIMEOUT_SECONDS = 10.0


async def check_site(site: Site, session: AsyncSession) -> Check:
    status_code = None
    response_time_ms = None
    is_available = False

    start_time = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http_client:
            response = await http_client.get(str(site.url))
        response_time_ms = (time.monotonic() - start_time) * 1000
        status_code = response.status_code
        is_available = 200 <= status_code <= 399
    except httpx.HTTPError:
        response_time_ms = (time.monotonic() - start_time) * 1000

    check = Check(
        site_id=site.id,
        is_available=is_available,
        status_code=status_code,
        response_time_ms=round(response_time_ms, 2),
    )
    session.add(check)
    return check


@router.post("/run", response_model=RunChecksResponseSchema)
async def run_checks(session: AsyncSession = Depends(get_db)) -> RunChecksResponseSchema:
    """Запускает параллельную проверку всех сайтов и сохраняет результаты в БД."""
    sites_result = await session.execute(select(Site))
    all_sites = list(sites_result.scalars().all())

    tasks: list[asyncio.Task[Check]] = []
    async with asyncio.TaskGroup() as task_group:
        for site in all_sites:
            tasks.append(task_group.create_task(check_site(site, session)))
    completed_checks = [task.result() for task in tasks]

    await session.commit()
    for check in completed_checks:
        await session.refresh(check)

    available_count = sum(1 for check in completed_checks if check.is_available)

    return RunChecksResponseSchema(
        total=len(completed_checks),
        available=available_count,
        unavailable=len(completed_checks) - available_count,
        results=[CheckResponseSchema.model_validate(check) for check in completed_checks],
    )


@router.get("/latest", response_model=list[CheckResponseSchema])
async def get_latest_checks(
    session: AsyncSession = Depends(get_db),
) -> list[Check]:
    result = await session.execute(select(Check).order_by(Check.checked_at.desc()))
    return list(result.scalars().all())
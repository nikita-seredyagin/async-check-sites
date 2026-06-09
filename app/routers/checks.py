import asyncio
import time

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Check, Site
from app.schemas import CheckResponseSchema, RunChecksResponseSchema

router = APIRouter(prefix="/checks", tags=["checks"])

REQUEST_TIMEOUT_SECONDS = 10.0


async def check_site(site: Site, http_client: httpx.AsyncClient, session: AsyncSession) -> Check:
    status_code = None
    response_time_ms = None
    is_available = False

    start_time = time.monotonic()
    try:
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


@router.post("/run", response_model=RunChecksResponseSchema, status_code=status.HTTP_200_OK)
async def run_checks(session: AsyncSession = Depends(get_db)) -> RunChecksResponseSchema:
    """Запускает параллельную проверку всех сайтов и сохраняет результаты в БД."""
    sites_result = await session.execute(select(Site))
    all_sites = list(sites_result.scalars().all())

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http_client:
        tasks: list[asyncio.Task[Check]] = []
        async with asyncio.TaskGroup() as task_group:
            for site in all_sites:
                tasks.append(task_group.create_task(check_site(site, http_client, session)))
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


@router.get("/latest", response_model=list[CheckResponseSchema], status_code=status.HTTP_200_OK)
async def get_latest_checks(
    session: AsyncSession = Depends(get_db),
) -> list[Check]:
    latest_check_ids = select(func.max(Check.id)).group_by(Check.site_id)
    result = await session.execute(
        select(Check).where(Check.id.in_(latest_check_ids)).order_by(Check.site_id)
    )
    return list(result.scalars().all())
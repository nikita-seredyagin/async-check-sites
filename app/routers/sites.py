from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Site
from app.schemas import SiteCreateSchema, SiteResponseSchema

router = APIRouter(prefix="/sites", tags=["sites"])


@router.post("", response_model=SiteResponseSchema, status_code=status.HTTP_201_CREATED)
async def add_site(
    site_data: SiteCreateSchema,
    session: AsyncSession = Depends(get_db),
) -> Site:
    url_string = str(site_data.url)

    existing = await session.scalar(select(Site).where(Site.url == url_string))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site with url '{url_string}' already exists",
        )

    site = Site(name=site_data.name, url=url_string)
    session.add(site)
    await session.commit()
    await session.refresh(site)
    return site


@router.get("", response_model=list[SiteResponseSchema])
async def list_sites(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[Site]:
    result = await session.execute(select(Site).order_by(Site.id).limit(limit).offset(offset))
    return list(result.scalars().all())
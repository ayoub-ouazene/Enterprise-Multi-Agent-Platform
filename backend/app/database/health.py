from typing import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session


async def check_database_health(session: AsyncSession) -> bool:
    try:
        result = await session.execute(text("SELECT 1"))
        return result.scalar_one() == 1
    except SQLAlchemyError:
        return False


async def get_database_health(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> bool:
    return await check_database_health(session)

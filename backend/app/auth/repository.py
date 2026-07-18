from datetime import datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken


def hash_token_identifier(jti: str) -> str:
    return sha256(jti.encode("utf-8")).hexdigest()


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_rotation(
        self,
        *,
        jti_hash: str,
        company_id: UUID,
        user_id: UUID,
    ) -> RefreshToken | None:
        return await self.session.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.jti_hash == jti_hash,
                RefreshToken.company_id == company_id,
                RefreshToken.user_id == user_id,
            )
            .with_for_update()
        )

    async def create(
        self,
        *,
        company_id: UUID,
        user_id: UUID,
        jti_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            company_id=company_id,
            user_id=user_id,
            jti_hash=jti_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def revoke(
        self,
        *,
        token_id: UUID,
        company_id: UUID,
        user_id: UUID,
        revoked_at: datetime,
        replaced_by_token_id: UUID,
    ) -> bool:
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.id == token_id,
                RefreshToken.company_id == company_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(
                revoked_at=revoked_at,
                replaced_by_token_id=replaced_by_token_id,
            )
        )
        return bool(result.rowcount)

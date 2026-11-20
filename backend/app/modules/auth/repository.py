import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import set_rls_business_context, set_rls_user_context
from app.db.base import Base  # noqa: F401 - asegura inicialización de Base antes de models
from app.modules.auth.models import Business, BusinessUser


@dataclass(frozen=True, slots=True)
class MembershipWithBusiness:
    """Resultado de membresía y comercio asociado para un usuario."""

    business: Business
    role: str


class AuthRepository:
    """Repositorio de autenticación y onboarding bajo contexto RLS."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[None]:
        """Usa savepoint si ya hay una transacción activa en la sesión, o abre una nueva."""
        if self._session.in_transaction():
            async with self._session.begin_nested():
                yield
        else:
            async with self._session.begin():
                yield

    async def get_user_membership(self, user_id: uuid.UUID) -> MembershipWithBusiness | None:
        """Resuelve membresía y comercio en dos pasos respetando políticas RLS."""
        async with self._transaction():
            await set_rls_user_context(self._session, user_id)

            membership_stmt = select(BusinessUser).where(BusinessUser.user_id == user_id)
            membership = (await self._session.execute(membership_stmt)).scalar_one_or_none()
            if membership is None:
                return None

            await set_rls_business_context(self._session, membership.business_id)

            business_stmt = select(Business).where(Business.id == membership.business_id)
            business = (await self._session.execute(business_stmt)).scalar_one_or_none()
            if business is None:
                return None

            return MembershipWithBusiness(business=business, role=membership.role)

    async def create_business_with_owner(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        country: str,
        timezone: str,
    ) -> Business:
        """Crea comercio y membresía owner en una transacción atómica bajo RLS."""
        business_id = uuid.uuid4()
        async with self._transaction():
            await set_rls_user_context(self._session, user_id)
            await set_rls_business_context(self._session, business_id)

            insert_biz_stmt = (
                insert(Business)
                .values(
                    id=business_id,
                    name=name,
                    country=country,
                    timezone=timezone,
                )
                .returning(Business)
            )
            business = (await self._session.execute(insert_biz_stmt)).scalar_one()

            insert_bu_stmt = insert(BusinessUser).values(
                business_id=business_id,
                user_id=user_id,
                role="owner",
            )
            await self._session.execute(insert_bu_stmt)

            return business

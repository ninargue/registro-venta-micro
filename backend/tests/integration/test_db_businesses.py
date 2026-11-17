import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_insert_business_valid(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    async with db_session.begin():
        await db_session.execute(
            text(
                """
                INSERT INTO businesses (id, name, country, timezone)
                VALUES (:id, :name, :country, :timezone)
                """
            ),
            {
                "id": business_id,
                "name": "Kiosco San Martin",
                "country": "AR",
                "timezone": "America/Argentina/Buenos_Aires",
            },
        )
        result = await db_session.execute(
            text("SELECT id, name, country, timezone FROM businesses WHERE id = :id"),
            {"id": business_id},
        )
        row = result.mappings().one()
        assert str(row["id"]) == business_id
        assert row["name"] == "Kiosco San Martin"
        assert row["country"] == "AR"
        assert row["timezone"] == "America/Argentina/Buenos_Aires"


@pytest.mark.asyncio
async def test_insert_business_rejects_nulls(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    with pytest.raises((IntegrityError, DBAPIError)):
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, NULL, 'AR', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"id": business_id},
            )


@pytest.mark.asyncio
async def test_insert_business_rejects_invalid_country_length(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    with pytest.raises((IntegrityError, DBAPIError)):
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, 'Test Store', 'ARG', 'America/Argentina/Buenos_Aires')
                    """
                ),
                {"id": business_id},
            )


@pytest.mark.asyncio
async def test_business_users_membership_and_valid_role(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    async with db_session.begin():
        await db_session.execute(
            text(
                """
                INSERT INTO businesses (id, name, country, timezone)
                VALUES (:id, :name, :country, :timezone)
                """
            ),
            {
                "id": business_id,
                "name": "Ferreteria Central",
                "country": "UY",
                "timezone": "America/Montevideo",
            },
        )
        await db_session.execute(
            text(
                """
                INSERT INTO business_users (business_id, user_id, role)
                VALUES (:b_id, :u_id, :role)
                """
            ),
            {"b_id": business_id, "u_id": user_id, "role": "owner"},
        )
        res = await db_session.execute(
            text("SELECT role FROM business_users WHERE business_id = :b_id AND user_id = :u_id"),
            {"b_id": business_id, "u_id": user_id},
        )
        assert res.scalar_one() == "owner"


@pytest.mark.asyncio
async def test_business_users_rejects_invalid_role(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    with pytest.raises((IntegrityError, DBAPIError)):
        async with db_session.begin():
            await db_session.execute(
                text(
                    """
                    INSERT INTO businesses (id, name, country, timezone)
                    VALUES (:id, 'Almacen', 'CL', 'America/Santiago')
                    """
                ),
                {"id": business_id},
            )
            await db_session.execute(
                text(
                    """
                    INSERT INTO business_users (business_id, user_id, role)
                    VALUES (:b_id, :u_id, 'superadmin')
                    """
                ),
                {"b_id": business_id, "u_id": user_id},
            )


@pytest.mark.asyncio
async def test_business_users_cascade_delete(db_session: AsyncSession) -> None:
    business_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    async with db_session.begin():
        await db_session.execute(
            text(
                """
                INSERT INTO businesses (id, name, country, timezone)
                VALUES (:id, 'Panaderia', 'AR', 'America/Argentina/Buenos_Aires')
                """
            ),
            {"id": business_id},
        )
        await db_session.execute(
            text(
                """
                INSERT INTO business_users (business_id, user_id, role)
                VALUES (:b_id, :u_id, 'owner')
                """
            ),
            {"b_id": business_id, "u_id": user_id},
        )
        await db_session.execute(
            text("DELETE FROM businesses WHERE id = :id"),
            {"id": business_id},
        )
        res = await db_session.execute(
            text("SELECT count(*) FROM business_users WHERE business_id = :b_id"),
            {"b_id": business_id},
        )
        assert res.scalar_one() == 0


@pytest.mark.asyncio
async def test_rls_isolation_by_session_variable(db_session: AsyncSession) -> None:
    b1 = str(uuid.uuid4())
    b2 = str(uuid.uuid4())
    async with db_session.begin():
        await db_session.execute(
            text(
                """
                INSERT INTO businesses (id, name, country, timezone) VALUES
                (:b1, 'Negocio 1', 'AR', 'America/Argentina/Buenos_Aires'),
                (:b2, 'Negocio 2', 'AR', 'America/Argentina/Buenos_Aires')
                """
            ),
            {"b1": b1, "b2": b2},
        )

        # Set tenant context to b1
        await db_session.execute(text(f"SET LOCAL app.current_business_id = '{b1}'"))
        result = await db_session.execute(text("SELECT id FROM businesses"))
        ids = [str(r[0]) for r in result.fetchall()]
        assert b1 in ids
        assert b2 not in ids

        # No tenant context set -> should return empty under RLS
        await db_session.execute(text("SET LOCAL app.current_business_id = ''"))
        result_empty = await db_session.execute(text("SELECT id FROM businesses"))
        assert len(result_empty.fetchall()) == 0

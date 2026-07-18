import argparse
import asyncio
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import InvalidPasswordError, hash_password
from app.companies.repository import CompanyRepository
from app.companies.schemas import CompanyCreate
from app.core.config import get_settings, validate_auth_configuration
from app.core.enums import ActorType
from app.core.exceptions import ConflictError
from app.database.session import create_database_engine, create_session_factory
from app.database import models as database_models
from app.users.repository import UserRepository


_ = database_models


async def bootstrap_company_account(
    session: AsyncSession,
    *,
    company_name: str,
    company_slug: str,
    email: str,
    password: str,
) -> None:
    company_payload = CompanyCreate(
        name=company_name.strip(),
        slug=company_slug.strip().lower(),
    )
    normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).casefold()
    encoded_password = hash_password(password)
    companies = CompanyRepository(session)

    try:
        if await companies.get_by_slug(company_payload.slug) is not None:
            raise ConflictError("Company slug already exists")
        company = await companies.create(company_payload.model_dump())
        users = UserRepository(session, company.id)
        await users.create(
            email=normalized_email,
            actor_type=ActorType.COMPANY,
            is_active=True,
            password_hash=encoded_password,
        )
        await session.commit()
    except ConflictError:
        await session.rollback()
        raise
    except IntegrityError:
        await session.rollback()
        raise ConflictError("Company or account already exists") from None
    except Exception:
        await session.rollback()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the first local Company account without exposing its password."
    )
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-slug", required=True)
    parser.add_argument("--email", required=True)
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    settings = get_settings()
    validate_auth_configuration(settings)
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            await bootstrap_company_account(
                session,
                company_name=args.company_name,
                company_slug=args.company_slug.strip().lower(),
                email=args.email,
                password=password,
            )
    finally:
        await engine.dispose()

    print("Development Company account created successfully.")


def main() -> None:
    try:
        asyncio.run(run())
    except (ConflictError, InvalidPasswordError, ValidationError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()

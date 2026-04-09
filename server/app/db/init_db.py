import structlog
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.db.session import async_session, engine
from app.models.base import Base
from app.models.user import User

logger = structlog.get_logger()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == settings.admin_email))
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                full_name="System Admin",
                role="admin",
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("admin_created", email=settings.admin_email)

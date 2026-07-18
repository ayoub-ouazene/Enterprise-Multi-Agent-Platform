from dataclasses import dataclass
from uuid import UUID

from app.core.enums import ActorType


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Trusted authorization context assembled from verified database records."""

    user_id: UUID
    company_id: UUID
    email: str
    actor_type: ActorType
    employee_id: UUID | None = None
    department_id: UUID | None = None
    is_manager: bool = False
    permissions: tuple[str, ...] = ()

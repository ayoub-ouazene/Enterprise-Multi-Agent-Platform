from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.requests.models import BusinessRequest


def can_view_business_request(
    current_user: AuthenticatedUser,
    business_request: BusinessRequest,
) -> bool:
    if business_request.company_id != current_user.company_id:
        return False
    if current_user.actor_type == ActorType.COMPANY:
        return True
    if business_request.requester_user_id == current_user.user_id:
        return True
    if current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
        department_id = current_user.department_id
        return department_id is not None and department_id in {
            business_request.owner_department_id,
            business_request.active_department_id,
        }
    return False

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.departments.repository import DepartmentRepository
from app.rag.enums import KnowledgeAccessScope, KnowledgeDepartmentScope
from app.rag.exceptions import KnowledgePermissionError
from app.rag.models import KnowledgeDocument
from app.rag.schemas import KnowledgeDocumentMetadata


MANAGER_ACCESS_SCOPES = (
    KnowledgeAccessScope.ALL_AUTHENTICATED,
    KnowledgeAccessScope.EMPLOYEES,
    KnowledgeAccessScope.DEPARTMENT_MANAGERS,
)
COMPANY_ACCESS_SCOPES = tuple(KnowledgeAccessScope)


async def trusted_manager_department(
    current_user: AuthenticatedUser,
    department_repository: DepartmentRepository,
) -> KnowledgeDepartmentScope:
    if (
        current_user.actor_type != ActorType.DEPARTMENT_MANAGER
        or not current_user.is_manager
        or current_user.department_id is None
    ):
        raise KnowledgePermissionError("Knowledge management access is required")
    department = await department_repository.get_by_id(current_user.department_id)
    if department is None or not department.is_active:
        raise KnowledgePermissionError("An active department is required")
    return KnowledgeDepartmentScope(department.department_type.value)


async def authorize_metadata(
    current_user: AuthenticatedUser,
    metadata: KnowledgeDocumentMetadata,
    department_repository: DepartmentRepository,
) -> None:
    if current_user.actor_type == ActorType.COMPANY:
        return
    own_department = await trusted_manager_department(
        current_user, department_repository
    )
    if metadata.department_scope != [own_department]:
        raise KnowledgePermissionError(
            "Managers may manage only their own department documents"
        )
    if metadata.access_scope not in MANAGER_ACCESS_SCOPES:
        raise KnowledgePermissionError("The selected access scope is not permitted")


async def authorize_document_management(
    current_user: AuthenticatedUser,
    document: KnowledgeDocument,
    department_repository: DepartmentRepository,
) -> None:
    if current_user.actor_type == ActorType.COMPANY:
        return
    own_department = await trusted_manager_department(
        current_user, department_repository
    )
    if document.department_scope != [own_department]:
        raise KnowledgePermissionError(
            "Managers may manage only their own department documents"
        )

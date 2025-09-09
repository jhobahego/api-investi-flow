# Importar todos los esquemas para facilitar su uso
from .attachment import (
    AttachmentBase,
    AttachmentCreate,
    AttachmentListResponse,
    AttachmentResponse,
    AttachmentUpdate,
)
from .phase import (
    PhaseBase,
    PhaseCreate,
    PhaseDetailResponse,
    PhaseListResponse,
    PhaseResponse,
    PhaseUpdate,
    PhaseWithTasksResponse,
)
from .project import (
    ProjectBase,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithPhasesResponse,
)
from .task import (
    TaskBase,
    TaskCreate,
    TaskDetailResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from .token import Token, TokenData
from .user import UserBase, UserCreate, UserInDB, UserResponse, UserUpdate

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserInDB",
    "UserUpdate",
    # Project schemas
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectWithPhasesResponse",
    "ProjectDetailResponse",
    # Phase schemas
    "PhaseBase",
    "PhaseCreate",
    "PhaseUpdate",
    "PhaseResponse",
    "PhaseListResponse",
    "PhaseWithTasksResponse",
    "PhaseDetailResponse",
    # Task schemas
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskListResponse",
    "TaskDetailResponse",
    # Attachment schemas
    "AttachmentBase",
    "AttachmentCreate",
    "AttachmentUpdate",
    "AttachmentResponse",
    "AttachmentListResponse",
    # Token schemas
    "Token",
    "TokenData",
]

# Importar todos los modelos para que SQLAlchemy los reconozca
from app.models.attachment import Attachment
from app.models.conversation import Conversation, Message
from app.models.phase import Phase
from app.models.project import Project
from app.models.task import Task
from app.models.user import User

__all__ = ["User", "Project", "Task", "Phase", "Attachment", "Conversation", "Message"]

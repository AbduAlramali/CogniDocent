"""Domain exceptions for the database / repository layer.

Decouples database-specific exceptions (like SQLAlchemy IntegrityError or NoResultFound)
from the service and application layers.
"""

import uuid
from typing import Any


class RepositoryError(Exception):
    """Base exception for all repository and database operations."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EntityNotFoundError(RepositoryError):
    """Base exception when a requested database entity is not found."""
    def __init__(self, entity_name: str, identifier: Any):
        self.entity_name = entity_name
        self.identifier = identifier
        super().__init__(f"{entity_name} with identifier '{identifier}' was not found.")


class DuplicateEntityError(RepositoryError):
    """Base exception when a database entity already exists (unique/integrity constraint)."""
    def __init__(self, entity_name: str, field_name: str, value: Any):
        self.entity_name = entity_name
        self.field_name = field_name
        self.value = value
        super().__init__(f"A {entity_name} with {field_name}='{value}' already exists.")


# Not Found Exceptions
class ProjectNotFoundError(EntityNotFoundError):
    def __init__(self, project_id: uuid.UUID):
        super().__init__("Project", project_id)


class DocumentNotFoundError(EntityNotFoundError):
    def __init__(self, doc_id: uuid.UUID):
        super().__init__("Document", doc_id)


class DocumentChunkNotFoundError(EntityNotFoundError):
    def __init__(self, identifier: Any):
        super().__init__("DocumentChunk", identifier)


class ChatNotFoundError(EntityNotFoundError):
    def __init__(self, chat_id: uuid.UUID):
        super().__init__("Chat", chat_id)


class MessageNotFoundError(EntityNotFoundError):
    def __init__(self, message_id: uuid.UUID):
        super().__init__("Message", message_id)


class MediaNotFoundError(EntityNotFoundError):
    def __init__(self, media_id: uuid.UUID):
        super().__init__("Media", media_id)


class ProviderSettingsNotFoundError(EntityNotFoundError):
    def __init__(self, identifier: Any):
        super().__init__("ProviderSettings", identifier)


# Duplicate Entity Exceptions
class DuplicateProjectError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("Project", field_name, value)


class DuplicateDocumentError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("Document", field_name, value)


class DuplicateChunkError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("DocumentChunk", field_name, value)


class DuplicateChatError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("Chat", field_name, value)


class DuplicateMessageError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("Message", field_name, value)


class DuplicateMediaError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("Media", field_name, value)


class DuplicateProviderSettingsError(DuplicateEntityError):
    def __init__(self, field_name: str, value: Any):
        super().__init__("ProviderSettings", field_name, value)

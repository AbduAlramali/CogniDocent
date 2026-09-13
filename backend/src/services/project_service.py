import hashlib
import io
from typing import Optional
import uuid

from src.core.config import MinioSettings
from src.core.enums import UploadStatus
from src.core.exceptions.antivirus_exceptions import AntivirusError
from src.core.exceptions.chat_exceptions import EmptyFileContentError
from src.core.exceptions.database import ProjectNotFoundError
from src.core.interfaces.iantivirus_service import IAntivirusService
from src.core.interfaces.idocument_repository import IDocumentRepository
from src.core.interfaces.ilogger import ILogger
from src.core.interfaces.iobject_repository import IObjectRepository
from src.core.interfaces.iproject_repository import IProjectRepository
from src.models.document import Document
from src.models.project import Project
from src.schemas.project import ProjectCreatedResponse, ProjectResponse
from src.services.pdf_service import PDFService
from src.services.thumbnail_service import ThumbnailService


class ProjectService:
    """
    Business service orchestrating project creation, document association,
    antivirus scanning, thumbnail generation, retrieval, and deletion.
    """

    def __init__(
        self,
        project_repo: IProjectRepository,
        doc_repo: IDocumentRepository,
        pdf_service: PDFService,
        thumbnail_service: ThumbnailService,
        antivirus: IAntivirusService,
        storage: IObjectRepository,
        minio_settings: MinioSettings,
        logger: ILogger,
    ) -> None:
        self.project_repo = project_repo
        self.doc_repo = doc_repo
        self.pdf_service = pdf_service
        self.thumbnail_service = thumbnail_service
        self.antivirus = antivirus
        self.storage = storage
        self.minio_settings = minio_settings
        self.logger = logger

    async def create_project(
        self,
        file_bytes: bytes,
        filename: str,
        title: Optional[str] = None,
    ) -> ProjectCreatedResponse:
        """
        Creates a new project linked to an uploaded PDF document:
        1. Validates file content
        2. Computes file hash
        3. Executes antivirus scan
        4. Generates and uploads thumbnails
        5. Saves document record with thumbnails JSON
        6. Parses and embeds chunks
        7. Creates and returns the project
        """
        if not file_bytes:
            raise EmptyFileContentError(filename)

        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 1. Antivirus check
        file_stream = io.BytesIO(file_bytes)
        is_clean = self.antivirus.scan_file(file_stream)
        if not is_clean:
            self.logger.error("Malicious file rejected during project creation", filename=filename)
            raise AntivirusError(f"Malicious content detected in file: {filename}")

        doc_id = uuid.uuid4()

        # 2. Thumbnail generation
        thumbnails_dict = self.thumbnail_service._generate_pdf_thumbnails(
            file_bytes, self.thumbnail_service.specs
        )
        uploaded_thumbnails: dict[str, str] = {}
        for tier, data in thumbnails_dict.items():
            thumb_key = f"thumbnails/{doc_id}/{tier}.jpg"
            await self.storage.upload_object(
                object_name=thumb_key,
                data=data,
                content_type="image/jpeg",
                bucket=self.minio_settings.THUMBNAILS_BUCKET,
            )
            uploaded_thumbnails[tier] = thumb_key

        # 3. Save PDF object to trusted storage
        object_name = f"documents/{doc_id}/{filename}"
        await self.storage.upload_object(
            object_name=object_name,
            data=file_bytes,
            content_type="application/pdf",
            bucket=self.minio_settings.TRUSTED_BUCKET,
        )

        # 4. Save Document in DB
        document = Document(
            doc_id=doc_id,
            file_path=object_name,
            file_size_bytes=len(file_bytes),
            file_hash=file_hash,
            content_type="application/pdf",
            status=UploadStatus.COMPLETED.value,
            primary_name=filename,
            thumbnails=uploaded_thumbnails if uploaded_thumbnails else None,
        )
        await self.doc_repo.create(document)

        # 5. Parse and embed document chunks
        try:
            await self.pdf_service.parse_and_embed_document(doc_id, file_bytes)
        except Exception as e:
            self.logger.warning(
                "Document chunk embedding completed with warnings",
                doc_id=doc_id,
                exc=e,
            )

        # 6. Save Project in DB
        project_id = uuid.uuid4()
        project = Project(
            project_id=project_id,
            doc_id=doc_id,
            title=title or filename,
        )
        await self.project_repo.create(project)

        self.logger.info(
            "Project created successfully",
            project_id=project_id,
            doc_id=doc_id,
            thumbnails=list(uploaded_thumbnails.keys()),
        )
        return ProjectCreatedResponse(project_id=project_id, doc_id=doc_id)

    async def list_projects(self) -> list[ProjectResponse]:
        """
        Lists all projects with their associated document thumbnails.
        """
        projects = await self.project_repo.list_all()
        responses: list[ProjectResponse] = []
        for p in projects:
            doc = await self.doc_repo.get_by_id(p.doc_id)
            thumbnails = doc.thumbnails if doc else None
            responses.append(
                ProjectResponse(
                    project_id=p.project_id,
                    doc_id=p.doc_id,
                    title=p.title,
                    description=p.description,
                    is_archived=p.is_archived,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                    thumbnails=thumbnails,
                )
            )
        return responses

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        """
        Deletes a project by ID.
        """
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return await self.project_repo.delete(project_id)

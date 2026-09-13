from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status

from src.dependencies import get_project_service
from src.schemas.project import ProjectCreatedResponse, ProjectResponse
from src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="""
    Uploads a PDF document as a stream of bytes, scans it for malware, generates thumbnail tiers
    (small, medium, large) stored as JSON metadata on the document record, links the document to
    a newly created project, triggers vector chunking/embedding, and returns the project_id and document_id.
    """,
    responses={
        201: {
            "description": "Project successfully created with linked document and thumbnails.",
            "model": ProjectCreatedResponse,
        },
        400: {"description": "Bad Request: Empty file content or invalid parameters."},
        422: {
            "description": "Unprocessable Entity: Document corrupted or unparseable."
        },
        500: {
            "description": "Internal Server Error: Antivirus failure or database error."
        },
    },
)
async def create_project(
    file: UploadFile = File(..., description="PDF document stream to upload"),
    title: Optional[str] = Form(None, description="Optional custom project title"),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCreatedResponse:
    content = await file.read()
    return await project_service.create_project(
        file_bytes=content,
        filename=file.filename,
        title=title,
    )


@router.get(
    "",
    response_model=List[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List Projects",
    description="""
    Lists all projects in the system, including the thumbnail URLs/keys of each project's associated document.
    """,
    responses={
        200: {
            "description": "Successfully retrieved list of projects with document thumbnails.",
            "model": List[ProjectResponse],
        }
    },
)
async def list_projects(
    project_service: ProjectService = Depends(get_project_service),
) -> List[ProjectResponse]:
    return await project_service.list_projects()


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="""
    Permanently deletes a project, cascading removal to associated chat sessions, messages, and document records.
    """,
    responses={
        204: {"description": "Project successfully deleted."},
        404: {"description": "Not Found: Project ID does not exist."},
    },
)
async def delete_project(
    project_id: uuid.UUID = Path(..., description="UUID of the project to delete"),
    project_service: ProjectService = Depends(get_project_service),
) -> None:
    await project_service.delete_project(project_id)

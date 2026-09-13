import uuid
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from src.core.config import MinioSettings, get_minio_settings
from src.core.interfaces.idocument_repository import IDocumentRepository
from src.core.interfaces.iobject_repository import IObjectRepository
from src.dependencies import (
    get_document_repository,
    get_object_repository,
    get_pdf_service,
)
from src.schemas.document import PageDescriptionResponse
from src.services.pdf_service import PDFService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "/{document_id}/pages/{page_num}/description",
    response_model=PageDescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Page Description",
    description="""
    Generates a rich multimodal page description on demand using the Vision LLM,
    describing text, tables, figures, charts, and reading flow for the specified page.
    """,
    responses={
        200: {
            "description": "Page description successfully generated.",
            "model": PageDescriptionResponse,
        },
        404: {"description": "Not Found: Document or page number does not exist."},
    },
)
async def get_page_description(
    document_id: uuid.UUID = Path(..., description="UUID of the document"),
    page_num: int = Path(..., ge=1, description="1-indexed page number"),
    pdf_service: PDFService = Depends(get_pdf_service),
) -> PageDescriptionResponse:
    description = await pdf_service.get_page_description(
        doc_id=document_id,
        page_num=page_num,
    )
    return PageDescriptionResponse(
        document_id=document_id,
        page_num=page_num,
        description=description,
    )


@router.get(
    "/{document_id}/file",
    status_code=status.HTTP_200_OK,
    summary="Get Document File",
    description="Streams the raw PDF document bytes for viewing.",
    responses={
        200: {"description": "PDF file stream", "content": {"application/pdf": {}}},
        404: {"description": "Document not found."},
    },
)
async def get_document_file(
    document_id: uuid.UUID = Path(..., description="UUID of the document"),
    doc_repo: IDocumentRepository = Depends(get_document_repository),
    storage: IObjectRepository = Depends(get_object_repository),
    minio_settings: MinioSettings = Depends(get_minio_settings),
) -> Response:
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        data = await storage.download_object(
            object_name=doc.file_path,
            bucket=minio_settings.TRUSTED_BUCKET,
        )
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"File could not be retrieved from storage: {e}"
        )

    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{doc.primary_name}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get(
    "/{document_id}/thumbnail",
    status_code=status.HTTP_200_OK,
    summary="Get Document Thumbnail",
    description="Streams the JPEG thumbnail of the document for project cards.",
    responses={
        200: {"description": "JPEG thumbnail image", "content": {"image/jpeg": {}}},
        404: {"description": "Thumbnail not found."},
    },
)
async def get_document_thumbnail(
    document_id: uuid.UUID = Path(..., description="UUID of the document"),
    tier: str = Query(default="small", description="Thumbnail tier: small, medium, large"),
    doc_repo: IDocumentRepository = Depends(get_document_repository),
    storage: IObjectRepository = Depends(get_object_repository),
    minio_settings: MinioSettings = Depends(get_minio_settings),
) -> Response:
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    thumbnails = doc.thumbnails or {}
    thumb_key = (
        thumbnails.get(tier)
        or thumbnails.get("small")
        or thumbnails.get("medium")
        or thumbnails.get("large")
    )
    if not thumb_key:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    try:
        data = await storage.download_object(
            object_name=thumb_key,
            bucket=minio_settings.THUMBNAILS_BUCKET,
        )
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Thumbnail could not be retrieved: {e}"
        )

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )

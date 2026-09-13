import uuid
from fastapi import APIRouter, Depends, Path, status

from src.dependencies import get_pdf_service
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

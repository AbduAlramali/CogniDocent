import re
import uuid
from src.core.dtos.llm_provider_dtos import CitationMetadata
from src.core.interfaces.idocument_chunk_repository import IDocumentChunkRepository
from src.core.interfaces.idocument_repository import IDocumentRepository
from src.core.interfaces.ilogger import ILogger

REF_PATTERN = re.compile(r"\[ref:\s*([^\]]+)\]")


class CitationService:
    """
    Business service handling citation extraction, short ID mapping to save LLM tokens,
    intercepting responses, swapping short refs with DB chunk IDs, and fetching
    bounding box metadata.
    """

    def __init__(
        self,
        chunk_repo: IDocumentChunkRepository,
        doc_repo: IDocumentRepository,
        logger: ILogger,
    ) -> None:
        self.chunk_repo = chunk_repo
        self.doc_repo = doc_repo
        self.logger = logger
        self._short_to_uuid: dict[str, uuid.UUID] = {}
        self._uuid_to_short: dict[uuid.UUID, str] = {}

    def to_short_id(self, chunk_id: uuid.UUID) -> str:
        """
        Maps a chunk UUID to a compact random token to save LLM context tokens.
        """
        if chunk_id in self._uuid_to_short:
            return self._uuid_to_short[chunk_id]
        short_id = uuid.uuid4().hex[:6]
        self._uuid_to_short[chunk_id] = short_id
        self._short_to_uuid[short_id] = chunk_id
        return short_id

    def get_chunk_id(self, short_id: str) -> uuid.UUID:
        """
        Resolves a short ID or raw UUID back to the database chunk UUID.
        """
        if short_id in self._short_to_uuid:
            return self._short_to_uuid[short_id]
        return uuid.UUID(short_id)

    def extract_ref_tags(self, text: str) -> list[str]:
        """
        Extracts all unique citation placeholder tags in order of appearance.
        """
        matches = REF_PATTERN.findall(text)
        return list(dict.fromkeys(m.strip() for m in matches))

    async def build_citations(
        self, text: str, doc_id: uuid.UUID
    ) -> tuple[str, list[CitationMetadata]]:
        """
        Intercepts LLM response text, extracts unique [ref: chunk_*] tags,
        swaps the short ref tags in the text with database chunk IDs,
        queries metadata from the database, and returns the swapped raw text
        alongside the isolated array of CitationMetadata objects.
        """
        ref_tags = self.extract_ref_tags(text)
        if not ref_tags:
            return text, []

        doc = await self.doc_repo.get_by_id(doc_id)
        source_name = doc.primary_name if doc else "Document"

        citations: list[CitationMetadata] = []
        swapped_text = text

        for tag in ref_tags:
            candidate = tag[6:]
            chunk_uuid = self.get_chunk_id(candidate)
            db_ref = f"chunk_{chunk_uuid}"
            swapped_text = swapped_text.replace(f"[ref: {tag}]", f"[ref: {db_ref}]")

            chunk = await self.chunk_repo.get_by_id(chunk_uuid)
            if chunk:
                citations.append(
                    CitationMetadata(
                        ref_id=db_ref,
                        page=chunk.page_num,
                        bbox=chunk.bbox or [0.0, 0.0, 0.0, 0.0],
                        source_name=source_name,
                    )
                )

        self.logger.info(
            "Resolved and swapped citations for document",
            doc_id=doc_id,
            tag_count=len(ref_tags),
            resolved_count=len(citations),
        )
        return swapped_text, citations

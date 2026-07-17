from __future__ import annotations

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai

from doc2rag.config import Settings


class DocAiClient:
    """Thin wrapper around Document AI's synchronous process_document call."""

    def __init__(self, settings: Settings) -> None:
        self._processor_name = (
            f"projects/{settings.gcp_project_id}/locations/{settings.gcp_location}"
            f"/processors/{settings.docai_processor_id}"
        )
        api_endpoint = f"{settings.gcp_location}-documentai.googleapis.com"
        self._client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=api_endpoint)
        )

    def process(self, content: bytes, mime_type: str) -> documentai.Document:
        request = documentai.ProcessRequest(
            name=self._processor_name,
            raw_document=documentai.RawDocument(content=content, mime_type=mime_type),
        )
        result = self._client.process_document(request=request)
        return result.document

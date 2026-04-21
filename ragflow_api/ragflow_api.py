"""
Unified RAGFlow API Client

This module provides a single entrypoint class that aggregates all RAGFlow API modules.
"""

from typing import Optional

from .base import RagflowAPIBase
from .Dataset.dataset_api import DatasetRagflowAPI
from .Document.document_api import DocumentRagflowAPI
from .Search.search_api import SearchRagflowAPI
from .Tenant.tenant_api import TenantRagflowAPI
from .User.user_api import UserRagflowAPI
from .Video.video_api import VideoRagflowAPI


class RagflowAPI(RagflowAPIBase):
    """
    Unified RAGFlow API client providing access to all API modules.

    This class serves as a single entrypoint for all RAGFlow API operations,
    aggregating User, Dataset, Document, Search, and Tenant functionality.

    Attributes:
        user: UserRagflowAPI instance for authentication and user management
        dataset: DatasetRagflowAPI instance for dataset/knowledge base operations
        document: DocumentRagflowAPI instance for document and chunk management
        video: VideoRagflowAPI instance for YouTube video ingestion and completion polling
        search: SearchRagflowAPI instance for search app and retrieval operations
        tenant: TenantRagflowAPI instance for team/tenant management

    Args:
        hostname: The RAGFlow server hostname (e.g., "http://localhost:9380")
        public_key: Optional RSA public key string. If not provided, will attempt to load from public_key_path
        public_key_path: Optional path to public key file. Defaults to "conf/public.pem"
        version: API version string (default: "v1")

    Example:
        Basic usage with automatic public key loading:

        >>> import asyncio
        >>> from ragflow_api import RagflowAPI
        >>>
        >>> async def main():
        ...     # Initialize the unified API client
        ...     api = RagflowAPI("http://localhost:9380")
        ...
        ...     # Register a new user
        ...     success = await api.user.register_user(
        ...         "user@example.com",
        ...         "John Doe",
        ...         "secure_password"
        ...     )
        ...
        ...     # Get authentication token
        ...     token = await api.user.get_token("user@example.com", "secure_password")
        ...
        ...     # Create a dataset
        ...     from ragflow_api.Dataset import CreateDatasetRequest
        ...     dataset_req = CreateDatasetRequest(name="My Dataset")
        ...     dataset = await api.dataset.create_dataset(dataset_req, token)
        ...
        ...     # Upload a document
        ...     doc_result = await api.document.upload(
        ...         kb_id=dataset["id"],
        ...         file_path="path/to/document.pdf",
        ...         token=token
        ...     )
        ...
        ...     # Perform a search
        ...     from ragflow_api.Search import RetrievalRequest
        ...     search_req = RetrievalRequest(
        ...         kb_id=dataset["id"],
        ...         question="What is RAGFlow?"
        ...     )
        ...     results = await api.search.retrieval(search_req, token)
        ...
        ...     return results
        ...
        >>> asyncio.run(main())

        With custom public key:

        >>> api = RagflowAPI(
        ...     "http://localhost:9380",
        ...     public_key="-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----"
        ... )

        With custom public key file:

        >>> api = RagflowAPI(
        ...     "http://localhost:9380",
        ...     public_key_path="/path/to/custom/public.pem"
        ... )
    """

    def __init__(self, hostname: str, public_key: Optional[str] = None, public_key_path: Optional[str] = None, version: str = "v1"):
        """
        Initialize the unified RAGFlow API client.

        Args:
            hostname: The RAGFlow server hostname
            public_key: Optional RSA public key string
            public_key_path: Optional path to public key file
            version: API version (default: "v1")
        """
        super().__init__(hostname, public_key, public_key_path, version)

        # Initialize all API modules with the same configuration
        self.user = UserRagflowAPI(hostname, self.public_key, None, version)
        self.dataset = DatasetRagflowAPI(hostname, self.public_key, None, version)
        self.document = DocumentRagflowAPI(hostname, self.public_key, None, version)
        self.video = VideoRagflowAPI(hostname, self.public_key, None, version)
        self.search = SearchRagflowAPI(hostname, self.public_key, None, version)
        self.tenant = TenantRagflowAPI(hostname, self.public_key, None, version)

    def __repr__(self) -> str:
        """Return string representation of the API client."""
        return f"RagflowAPI(hostname='{self.hostname}', version='{self.base_url.split('/')[-1]}')"

    async def download_pdf_and_highlight(self, chunks: list, output_dir: str, token: str) -> dict:
        """
        Download the original PDFs for the given chunks, highlight their positions,
        and save the annotated PDFs to the specified output directory.
        Handles chunks from multiple documents automatically.

        Args:
            chunks: List of ChunkEntity objects. Can belong to one or more documents.
            output_dir: Directory to save the highlighted PDFs.
            token: Authentication token.

        Returns:
            Dictionary mapping document IDs to their highlighted PDF file paths.
            Example: {"doc123": "/path/to/highlighted_doc1.pdf", "doc456": "/path/to/highlighted_doc2.pdf"}
        """
        import os
        import fitz
        from collections import defaultdict

        if not chunks:
            raise ValueError("No chunks provided")

        # Group chunks by document ID
        chunks_by_doc = defaultdict(list)
        for chunk in chunks:
            # Handle both ChunkEntity (doc_id) and RetrievalChunk (document_id)
            d_id = getattr(chunk, "doc_id", getattr(chunk, "document_id", None))
            if d_id:
                chunks_by_doc[d_id].append(chunk)

        result_paths = {}

        # Process each document separately
        for doc_id, doc_chunks in chunks_by_doc.items():
            # Handle both ChunkEntity (docnm_kwd) and RetrievalChunk (document_keyword)
            doc_name = getattr(doc_chunks[0], "docnm_kwd", getattr(doc_chunks[0], "document_keyword", "document.pdf"))

            # 1. Download original PDF
            pdf_bytes = await self.document.download(doc_id, token)

            # 2. Open PDF with PyMuPDF
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # 3. Add highlights based on chunk positions
            # position format is generally [page_index, x0, y0, x1, y1] (or varied based on parsing, usually x0,y0,x1,y1)
            for chunk in doc_chunks:
                for pos in chunk.positions:
                    if len(pos) >= 5:
                        page_idx = int(pos[0]) - 1  # 1-based to 0-based
                        if 0 <= page_idx < len(pdf_doc):
                            page = pdf_doc[page_idx]
                            # Create rect from [x0, x1, y0, y1] or [x0, y0, x1, y1]
                            # RAGFlow returns [page_num, int, int, int, int]
                            # typically x0, x1, y0, y1
                            # Since we are not strictly sure of the coordinate format, assuming standard bounding box
                            # Let's try to interpret pos[1:] as [x0, x1, y0, y1]
                            x0, x1, y0, y1 = pos[1], pos[2], pos[3], pos[4]
                            rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                            try:
                                # Highlight the rect
                                highlight = page.add_highlight_annot(rect)
                                highlight.update()
                            except Exception as e:
                                print(f"Warning: Could not highlight rect {rect} on page {page_idx}: {e}")

            # 4. Save annotated PDF
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            output_path = os.path.join(output_dir, f"highlighted_{doc_name}")
            pdf_doc.save(output_path)
            pdf_doc.close()

            result_paths[doc_id] = output_path

            # 5. Download associated images
            for chunk in doc_chunks:
                if chunk.image_id:
                    try:
                        image_bytes = await self.document.download_image(chunk.image_id, token)
                        img_ext = chunk.image_id.split(".")[-1] if "." in chunk.image_id else "png"
                        img_filename = f"image_{chunk.image_id}"
                        if not img_filename.lower().endswith(f".{img_ext.lower()}"):
                            img_filename = f"{img_filename}.{img_ext}"

                        img_path = os.path.join(output_dir, img_filename)
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)
                    except Exception as e:
                        print(f"Warning: Could not download image {chunk.image_id}: {e}")

        return result_paths

    async def download_pages_and_highlight(self, chunks: list, output_dir: str, token: str) -> dict:
        """
        Download the original PDFs, extract only the pages containing the provided chunks,
        highlight the chunk positions, and save the subset PDFs.
        Handles chunks from multiple documents automatically.

        Args:
            chunks: List of ChunkEntity objects. Can belong to one or more documents.
            output_dir: Directory to save the highlighted PDF subsets.
            token: Authentication token.

        Returns:
            Dictionary mapping document IDs to their subset PDF file paths.
            Example: {"doc123": "/path/to/subset_doc1.pdf", "doc456": "/path/to/subset_doc2.pdf"}
        """
        import os
        import fitz
        from collections import defaultdict

        if not chunks:
            raise ValueError("No chunks provided")

        # Group chunks by document ID
        chunks_by_doc = defaultdict(list)
        for chunk in chunks:
            # Handle both ChunkEntity (doc_id) and RetrievalChunk (document_id)
            d_id = getattr(chunk, "doc_id", getattr(chunk, "document_id", None))
            if d_id:
                chunks_by_doc[d_id].append(chunk)

        result_paths = {}

        # Process each document separately
        for doc_id, doc_chunks in chunks_by_doc.items():
            # Handle both ChunkEntity (docnm_kwd) and RetrievalChunk (document_keyword)
            doc_name = getattr(doc_chunks[0], "docnm_kwd", getattr(doc_chunks[0], "document_keyword", "document.pdf"))

            # 1. Download original PDF
            pdf_bytes = await self.document.download(doc_id, token)

            # 2. Open PDF with PyMuPDF
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # 3. Identify target pages and add highlights
            target_pages = set()
            for chunk in doc_chunks:
                for pos in chunk.positions:
                    if len(pos) >= 5:
                        page_idx = int(pos[0]) - 1
                        target_pages.add(page_idx)

            # Convert to sorted list of page indices
            target_pages_list = sorted(list(page_idx for page_idx in target_pages if 0 <= page_idx < len(pdf_doc)))

            if not target_pages_list:
                # Fallback if no valid pages found
                target_pages_list = list(range(len(pdf_doc)))

            # Extract subset of pages
            subset_doc = fitz.open()
            for idx in target_pages_list:
                subset_doc.insert_pdf(pdf_doc, from_page=idx, to_page=idx)

            # 4. Add highlights to the subset doc
            # Because we only inserted specific pages, we need to map original page_idx to new page_idx
            page_mapping = {orig_idx: new_idx for new_idx, orig_idx in enumerate(target_pages_list)}

            for chunk in doc_chunks:
                for pos in chunk.positions:
                    if len(pos) >= 5:
                        orig_page_idx = int(pos[0]) - 1
                        if orig_page_idx in page_mapping:
                            new_page_idx = page_mapping[orig_page_idx]
                            page = subset_doc[new_page_idx]
                            x0, x1, y0, y1 = pos[1], pos[2], pos[3], pos[4]
                            rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                            try:
                                highlight = page.add_highlight_annot(rect)
                                highlight.update()
                            except Exception as e:
                                print(f"Warning: Could not highlight rect {rect} on page {new_page_idx}: {e}")

            # 5. Save subset PDF
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            output_path = os.path.join(output_dir, f"subset_highlighted_{doc_name}")
            subset_doc.save(output_path)
            subset_doc.close()
            pdf_doc.close()

            result_paths[doc_id] = output_path

            # 6. Download associated images
            for chunk in doc_chunks:
                if chunk.image_id:
                    try:
                        image_bytes = await self.document.download_image(chunk.image_id, token)
                        img_ext = chunk.image_id.split(".")[-1] if "." in chunk.image_id else "png"
                        img_filename = f"image_{chunk.image_id}"
                        if not img_filename.lower().endswith(f".{img_ext.lower()}"):
                            img_filename = f"{img_filename}.{img_ext}"

                        img_path = os.path.join(output_dir, img_filename)
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)
                    except Exception as e:
                        print(f"Warning: Could not download image {chunk.image_id}: {e}")

        return result_paths

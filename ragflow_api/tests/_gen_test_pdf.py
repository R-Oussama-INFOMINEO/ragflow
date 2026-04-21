"""Script to generate the bundled test PDF for ragflow_api.tests.data/"""
import pathlib

out = pathlib.Path("ragflow_api/tests/data/test.pdf")
out.parent.mkdir(parents=True, exist_ok=True)

# A minimal but structurally valid single-page PDF with rich readable text
# matching the queries used in the comprehensive test suite.
content_stream = (
    b"BT\n"
    b"/F1 18 Tf\n"
    b"50 750 Td\n"
    b"(RAGFlow API Doctor Test Document) Tj\n"
    b"0 -40 Td\n"
    b"/F1 12 Tf\n"
    b"(This document is used by the ragflow-api integration test suite.) Tj\n"
    b"0 -25 Td\n"
    b"(It verifies that the RAGFlow server can ingest, chunk and retrieve text.) Tj\n"
    b"0 -25 Td\n"
    b"(Children in historical societies were often dressed as miniature adults.) Tj\n"
    b"0 -25 Td\n"
    b"(Fashion mirrored social status and adult norms in child clothing design.) Tj\n"
    b"0 -25 Td\n"
    b"(The miniature adult design philosophy reflected limited childhood autonomy.) Tj\n"
    b"0 -25 Td\n"
    b"(Knowledge graphs capture structured relationships between these concepts.) Tj\n"
    b"0 -25 Td\n"
    b"(RAPTOR summarisation condenses lengthy documents into hierarchical chunks.) Tj\n"
    b"0 -25 Td\n"
    b"(Table of contents extraction improves navigation and retrieval accuracy.) Tj\n"
    b"ET\n"
)

cs_len = len(content_stream)

objects = [
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
    (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Resources << /Font << /F1 4 0 R >> >>\n"
        b"   /Contents 5 0 R >>\nendobj\n"
    ),
    b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    (
        b"5 0 obj\n"
        + f"<< /Length {cs_len} >>\n".encode()
        + b"stream\n"
        + content_stream
        + b"endstream\nendobj\n"
    ),
]

# Build the PDF binary
header = b"%PDF-1.4\n"
body = header
offsets = []
for obj in objects:
    offsets.append(len(body))
    body += obj

xref_offset = len(body)
xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
for off in offsets:
    xref += f"{off:010d} 00000 n \n".encode()

trailer = (
    f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
)

pdf_bytes = body + xref + trailer
out.write_bytes(pdf_bytes)
print(f"Written {len(pdf_bytes)} bytes  ->  {out}")

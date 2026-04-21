# RAGFlow: Layout Recognition & Parser Configuration Guide

In RAGFlow, the **Layout Recognition** and **Parser Configuration** (Chunking Methods) are the "brain" of your data ingestion. Choosing the right combination determines whether your LLM retrieves precise information or "jumbled garbage."

---

## 1. Layout Recognition (The "Eyes")
This setting primarily affects **PDF files**. It determines how RAGFlow "sees" the document structure (titles, tables, images vs. plain text).

| Recognition Method | Advantage | Disadvantage | Best Use Case |
| :--- | :--- | :--- | :--- |
| **DeepDoc (Default)** | **Extremely accurate.** Uses YOLOv8/TSR to detect tables, columns, and figures. Handles complex multi-column layouts like a human. | **Resource-heavy & Slow.** Running vision models for every page takes time and CPU/GPU. | Academic papers, Financial reports, multi-column brochures. |
| **Naive** | **Lightning Fast.** It ignores the layout and just "extracts" the text stream. | **Loses context.** In a 2-column PDF, it might read line 1 of column A then line 1 of column B, making the text unreadable. Fails on tables. | eBooks, simple word-to-pdf exports, plain text documents. |
| **MinerU / Docling** | **Machine Optimized.** These are specialized open-source tools that convert PDFs into clean Markdown/JSON. | **Experimental.** Requires external API setup (for MinerU). Performance can vary compared to DeepDoc. | High-volume batch processing where you already have a MinerU service. |
| **VLM (Vision LLM)** | **Deep Understanding.** Can describe what an image *means* (e.g., "A chart showing rising inflation"). | **Expensive & Very Slow.** Costs tokens for every page. Can hallucinate fine details in large tables. | Infographics, posters, or documents where image content is more important than text. |

---

## 2. Parser Config / Chunking Methods (The "Logic")
Once the layout is recognized, RAGFlow uses a **Chunking Template** to slice the text into pieces. This is crucial because LLMs have limited "context windows."

| Chunking Method | How it Works | Advantage | Why you should care? |
| :--- | :--- | :--- | :--- |
| **General (Naive)** | Slices by delimiters (`\n`, `.`) and merges until it hits a token limit (e.g., 512). | **Safe default.** Works for almost any file type. | Use this if your data is messy or doesn't follow a specific structure. |
| **Paper** | Detects **Abstract**, **Authors**, and **Sections**. Treats the abstract as a "hub" chunk. | **Highly structured.** Keeps logical sections together rather than cutting them mid-paragraph. | **Essential for Research.** It ensures the LLM knows a specific find belongs to the "Results" section, not "References." |
| **Table** | Each row in an Excel/CSV/Table becomes a chunk. Formats as `- Header: Value`. | **Structured Logic.** It treats each row as a "record," preventing the LLM from mixing data between rows. | **Business Data.** Use for product catalogs, employee lists, or data logs. |
| **Q&A** | Specifically looks for Question/Answer pairs (in Excel, MD, or PDF). | **High Precision.** Directly aligns the user's potential question with a pre-defined answer. | **Customer Support / FAQ.** Best for help centers where you already have a list of FAQs. |
| **Book** | Uses Table of Contents and Headers to group chapters. | **Logical Flow.** Keeps related themes together in long documents. | Long manuals, textbooks, or novels. |
| **Laws** | Understands numbering (Article 1, Clause 2.a). | **Legal Compliance.** Preserves the hierarchy of legal text which is vital for correct interpretation. | Contracts, government regulations, or compliance docs. |
| **Manual** | You define exactly where a chunk starts/ends via Regex or specific delimiters. | **Total Control.** You can ensure chunks never split across critical data points. | Custom proprietary formats or highly specific data structures. |

---

## Summary & Best Practices

Choosing the wrong combination leads to **Retrieval Failure**:

1.  **Context Loss**: If you use "Naive" recognition on a complex financial report, the numbers from Table A might get mixed with text from Table B. The LLM will then give you wrong budget figures.
2.  **Chunk Fragmentation**: Using "General" chunking on a law document might cut a sentence exactly where a "not" or "unless" appears, causing the LLM to give the opposite legal advice.
3.  **Efficiency vs. Accuracy**: If you have 10,000 pages of simple text, using **DeepDoc** is a waste of 90% of your time. Switching to **Naive** will make your ingestion 10x faster with the same accuracy.

**RAGFlow Pro-Tip:**
If your PDF has tables, **ALWAYS** use **DeepDoc** recognition with the **Table** or **General** parser. If it's a clean digital book, use **Naive** recognition with the **Book** parser.

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk(docs):
    # split by markdown headings first: each chunk keeps its section context
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False   # keep the heading inside the chunk text
    )

    # then split oversized sections by character count
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=300
    )

    all_chunks = []
    for doc in docs:
        # first split by headers
        header_chunks = header_splitter.split_text(doc.page_content)

        # then split large sections further
        for hchunk in header_chunks:
            sub_chunks = char_splitter.split_documents([hchunk])
            for sc in sub_chunks:
                # carry over parent file metadata into every chunk
                sc.metadata.update({
                    "source": doc.metadata.get("source"),
                    "filename": doc.metadata.get("filename"),
                    "title": doc.metadata.get("title"),
                    "headings": doc.metadata.get("headings"),
                    "date": doc.metadata.get("date"),
                    "all_dates": doc.metadata.get("all_dates"),
                    "type": doc.metadata.get("type"),
                })
                all_chunks.append(sc)

    return all_chunks
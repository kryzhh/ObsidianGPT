from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000, 
        chunk_overlap = 100
    )
    chunks = splitter.split_documents(docs)
    return chunks
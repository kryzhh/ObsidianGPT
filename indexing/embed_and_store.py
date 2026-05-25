from langchain_community.vectorstores import Chroma

def embed_and_store(embeddings,chunks):
    vectorstores = Chroma.from_documents(
        documents = chunks,
        embedding = embeddings,
        persist_directory = './chroma.db'
    )
    return vectorstores
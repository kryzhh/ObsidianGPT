import json
import os
from pathlib import Path
from langchain_ollama import OllamaEmbeddings

from indexing.load import load_file
from indexing.chunk import chunk
from indexing.embed_and_store import embed_and_store
from retrieval.retrieval import retrieve

from generation.generation import generation

EMBEDDINGS = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

# Load config
with open('.env.json', 'r') as file:
    ENV = json.load(file)

VAULT_DIR = ENV["VAULT"]
DB_PATH = "./chroma.db"

# Validate vault folder exists
if not Path(VAULT_DIR).exists():
    print("Invalid vault folder")
    quit(0)

# Index all files if db doesn't exist yet
if not Path(DB_PATH).exists():
    print("Indexing vault...")
    all_chunks = []

    # Walk through every file in the vault folder
    for root, dirs, files in os.walk(VAULT_DIR):
        for filename in files:
            filepath = os.path.join(root, filename)
            docs = load_file(filepath)
            if docs:                          # load_file returns None for non-.md files
                chunks = chunk(docs)
                all_chunks.extend(chunks)
                print(f"Indexed: {filepath}")

    vectorstore = embed_and_store(EMBEDDINGS, all_chunks)
    print(f"Done. {len(all_chunks)} chunks stored.")
else:
    print("DB already exists, skipping indexing.")
    # load existing db
    from langchain_community.vectorstores import Chroma
    vectorstore = Chroma(
        persist_directory=DB_PATH,
        embedding_function=EMBEDDINGS
    )

question = ""
while True:
    question = input("Enter your question (or 'quit'): ")
    if question.lower() == "quit":
        break

    retriever = retrieve(vectorstore, question)

    # DEBUG — see what chunks are actually being fetched
    # test_docs = retriever.invoke(question)
    # for i, doc in enumerate(test_docs):
    #     print(f"\n[Chunk {i+1}] source: {doc.metadata.get('source')}")
    #     print(doc.page_content[:100])
    # print("---")
    answer = generation(retriever, ENV["CHAT_MODEL"], question)
    print(answer)
    print('-------------------------------------------------------------------------')
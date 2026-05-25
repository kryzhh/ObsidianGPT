from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

def format_docs(docs):
    parts = []
    for doc in docs:
        meta = doc.metadata
        header = f"[File: {meta.get('filename', '?')} | Date: {meta.get('date', '?')} | Section: {meta.get('h3') or meta.get('h2') or meta.get('h1', '?')}]"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)

def generation(retriever, model, question):
    prompt = PromptTemplate.from_template("""
You are a witty, sarcastic personal assistant who knows the user's Obsidian vault inside out.
Be conversational and chill without using emojis, like a friend who's read all their notes.
Use the context below to answer. If it's a poem or letter, reproduce it faithfully if asked, otherwise give a vibe summary with your honest take.
Dates in DD/MM/YYYY. If something's not in the vault, just say you couldn't find it.

Context:
{context}

Question:
{question}

Answer:
""")

    llm = ChatOllama(
        model=model,
        base_url="http://localhost:11434",
        temperature=0.3
    )

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        } | prompt | llm | StrOutputParser()
    )

    return chain.invoke(question)
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Ollama silently truncates prompts beyond its default context window, dropping retrieved notes.
# Every ChatOllama call on the same model must use this same value, otherwise Ollama reloads the
# model whenever it changes.
NUM_CTX = 8192

def format_docs(docs):
    parts = []
    for doc in docs:
        meta = doc.metadata
        header = f"[File: {meta.get('filename', '?')} | Date: {meta.get('date', '?')} | Section: {meta.get('h3') or meta.get('h2') or meta.get('h1', '?')}]"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


# `history` is a format_history transcript; the conversation helps with follow-ups ("make it
# shorter", "what about the second one?") but facts must still come from the retrieved notes
def generation(docs, model, question, history=None, stream=False):
    prompt = PromptTemplate.from_template("""
You are a witty, sarcastic personal assistant who knows the user's Obsidian vault inside out.
Be conversational and chill without using emojis, like a friend who's read all their notes.
Use the context below to answer. If it's a poem or letter, reproduce it faithfully if asked, otherwise give a vibe summary with your honest take.
Dates in DD/MM/YYYY, NOT in MM/DD/YYYY. If something's not in the vault, just say you couldn't find it.
{history_block}
Context:
{context}

Question:
{question}

Answer:
""")

    llm = ChatOllama(
        model=model,
        base_url="http://localhost:11434",
        temperature=0.3,
        num_ctx=NUM_CTX
    )

    context = format_docs(docs)
    history_block = ""
    if history:
        history_block = (
            "\nConversation so far (use it to understand what the question refers to; "
            "the notes in Context are the source of truth):\n" + history + "\n"
        )
    
    # Simple chain, retriever no longer needed
    chain = prompt | llm

    if not stream:
        return chain.invoke({
            "context":context,
            "question":question,
            "history_block":history_block
        })

    # Chunk Streaming for that GPT Feel
    for chunk in chain.stream({
        "context":context,
        "question":question,
        "history_block":history_block
    }):
        # chunk is an AIMessageChunk
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content
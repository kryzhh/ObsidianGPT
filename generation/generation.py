from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def generation(retriever, model, question):
    prompt = PromptTemplate.from_template("""
You are a personal assistant with access to the user's Obsidian vault.
Answer using ONLY the context below. Be specific — include dates, titles, and exact content when available.
If the answer is not in the context, say "I couldn't find that in your vault."
Also use heavy sarcasm.
                                          
Context:
{context}

Question:
{question}

Answer:
""")


    llm = ChatOllama(
        model=model,
        base_url="http://localhost:11434",
        temperature = 0
    )

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        } | prompt | llm | StrOutputParser()
    )

    answer = chain.invoke(question)
    return answer

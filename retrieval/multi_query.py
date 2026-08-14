import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


# Extract quoted terms to use them as they are. Can be useful for situations where one directly cites something
# For eg: "Tell me the contents of 'The Final Unsent Letter'". Here 'The Final Unsent Letter' does not have to be paraphrased.
def _extract_quoted_terms(question):
    return re.findall(r'["\']([^"\']+)["\']', question)

# Return a list of queries produced by LLM in paraphrased form, else a single string where queries
# are seperated by new line characters
def _parse_queries(llm_output):
    queries = []
    for line in llm_output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # If the llm output contains numberings or bullets, remove them.
        line = re.sub(r'^\d+[\.\):\-]\s*', '', line)
        line = re.sub(r'^[-*•]\s*', '', line)
        if line:
            queries.append(line)
    return queries

def multi_query_retrieve(question, retriever, model, base_url="http://localhost:11434"):
    llm = ChatOllama(model=model, base_url=base_url, temperature=0.3)

    prompt = PromptTemplate.from_template("""
Generate 3 different phrasings of the following question to improve search over a personal knowledge base.
Output ONLY the 3 questions, one per line, no numbering, no explanation.

Original question: {question}

Alternative phrasings:
""")

    query_gen_chain = prompt | llm | StrOutputParser()

    raw = query_gen_chain.invoke({"question": question})
    alternatives = _parse_queries(raw)  # ← was missing

    # enforce quoted terms if present
    quoted_terms = _extract_quoted_terms(question)
    if quoted_terms:
        alternatives = [
            q for q in alternatives
            if all(term.lower() in q.lower() for term in quoted_terms)
        ]

    # always runs regardless of quoted terms
    all_queries = [question] + alternatives[:3]

    seen = set()
    all_docs = []
    for query in all_queries:
        docs = retriever.invoke(query)
        for doc in docs:
            doc_id = hash(doc.page_content)
            if doc_id not in seen:
                seen.add(doc_id)
                all_docs.append(doc)

    return all_docs
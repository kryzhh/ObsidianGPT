import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from generation.generation import NUM_CTX


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

PARAPHRASE_PROMPT = PromptTemplate.from_template("""
Generate 3 different phrasings of the following question to improve search over a personal knowledge base.
Output ONLY the 3 questions, one per line, no numbering, no explanation.

Original question: {question}

Alternative phrasings:
""")

# Follow-ups like "show me the whole thing" can't be searched as-is, so in a conversation the same
# call first rewrites the question to stand on its own. No extra LLM round trip for chat memory.
CONDENSE_PROMPT = PromptTemplate.from_template("""
You help search a personal notes vault. Below is a conversation and the user's latest question.

Conversation:
{history}

Latest question: {question}

First, rewrite the latest question as one standalone question that makes sense without the conversation.
Replace vague references ("it", "that letter", "the second point") with what they refer to, and keep note titles exactly as written.
If it is already standalone, repeat it unchanged.
Then write 3 different phrasings of that standalone question to improve search.

Output exactly these 4 lines and nothing else:
STANDALONE: <standalone question>
<phrasing 1>
<phrasing 2>
<phrasing 3>
""")

# Return [standalone question, *up to 3 paraphrases]. Without history the standalone question is
# the original one; with history (a format_history transcript) it's the LLM's rewrite.
def generate_queries(question, model, history=None, base_url="http://localhost:11434"):
    llm = ChatOllama(model=model, base_url=base_url, temperature=0.3, num_ctx=NUM_CTX)

    if history:
        raw = (CONDENSE_PROMPT | llm | StrOutputParser()).invoke({"history": history, "question": question})
        lines = _parse_queries(raw)
        standalone = next((l for l in lines if l.upper().startswith("STANDALONE:")), None)
        if standalone:
            lines.remove(standalone)
            question = standalone.split(":", 1)[1].strip() or question
        alternatives = lines
    else:
        raw = (PARAPHRASE_PROMPT | llm | StrOutputParser()).invoke({"question": question})
        alternatives = _parse_queries(raw)

    # enforce quoted terms if present
    quoted_terms = _extract_quoted_terms(question)
    if quoted_terms:
        alternatives = [
            q for q in alternatives
            if all(term.lower() in q.lower() for term in quoted_terms)
        ]

    # always runs regardless of quoted terms
    return [question] + alternatives[:3]

def multi_query_retrieve(question, retriever, model, base_url="http://localhost:11434"):
    all_queries = generate_queries(question, model, base_url=base_url)

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
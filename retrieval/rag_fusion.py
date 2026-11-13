# Standard RRF constant from the original paper (Cormack et al., 2009). Higher values flatten
# the gap between rank 1 and rank 10, so one query's top hit can't dominate the fused list.
RRF_K = 60


# Identify the same chunk across result lists. Chunk text alone isn't enough since two notes
# could contain an identical section, so pair it with the source file.
def _doc_key(doc):
    return (doc.metadata.get("source"), doc.page_content)

# Merge several ranked lists into one. Each doc scores sum(1 / (k + rank)) over every list it
# appears in, so docs that rank well for many phrasings of the question rise to the top.
def reciprocal_rank_fusion(ranked_lists, k=RRF_K):
    scores = {}
    docs = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            key = _doc_key(doc)
            docs.setdefault(key, doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)

    fused = sorted(scores, key=scores.get, reverse=True)
    return [(docs[key], scores[key]) for key in fused]

def rag_fusion_retrieve(queries, retriever, top_n=6):
    # run every query's similarity search concurrently, each returns its own ranked list
    ranked_lists = retriever.batch(queries)

    fused = reciprocal_rank_fusion(ranked_lists)
    return [doc for doc, _score in fused[:top_n]]

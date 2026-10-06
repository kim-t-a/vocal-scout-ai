import json

from services.chat import generate_answer

# NVIDIA's hosted catalog no longer serves a cross-encoder reranking model
# (probed live: the key's /v1/models lists 81 models, none a reranker, and
# every /v1/ranking and /v1/retrieval/.../reranking path returns 404). So the
# reranker is the chat model acting as a listwise judge: it sees the question
# and ALL candidate passages together — strictly more context than a
# bi-encoder's cosine similarity — and returns the passage order.
PER_PASSAGE_CHARS = 600   # keep the whole judge prompt compact


def _prompt(query: str, passages: list[str]) -> str:
    listing = "\n".join(
        f"[{index}] {passage[:PER_PASSAGE_CHARS]}"
        for index, passage in enumerate(passages)
    )

    return f"""You are a strict relevance judge for a video-tutor search index.

Rank the passages below by how well they answer the query. Judge only relevance
to the query — ignore style and length. Answer with ONLY a JSON array of the
passage numbers, best first, using every number exactly once. No prose, no
markdown fences.

Query: {query}

{listing}"""


def _parse_order(text: str, expected: int) -> list[int] | None:
    """
    Extract the model's ranking as a full permutation of passage indices.

    The prompt demands a bare JSON array, but the model may wrap it in prose or
    fences — so take the first [...] substring, keep the valid in-range indices
    in the order given, drop duplicates, then append any passages the model
    omitted (preserving input order). A complete ordering always comes back;
    None means nothing usable was parsed and the caller keeps its own order.
    """

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, list):
        return None

    seen: set[int] = set()
    ordered: list[int] = []

    for item in data:
        if isinstance(item, int) and 0 <= item < expected and item not in seen:
            seen.add(item)
            ordered.append(item)

    ordered.extend(index for index in range(expected) if index not in seen)

    return ordered or None


def rerank(query: str, passages: list[str]) -> list[int] | None:
    """
    Order passages best-to-worst for the query.

    Returns passage INDICES (best first — a permutation of range(len(passages)))
    or None when the judge is unavailable or unparseable, in which case the
    caller keeps its pre-rerank order instead of blocking the answer.
    """

    if not passages:
        return None

    answer = generate_answer(_prompt(query, passages))

    if answer is None:
        print("Reranker judge unavailable, keeping fusion order.")
        return None

    return _parse_order(answer, len(passages))

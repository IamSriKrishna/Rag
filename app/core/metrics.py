from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "rag_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_DURATION = Histogram(
    "rag_http_request_duration_seconds", "HTTP request duration", ["method", "route"]
)
RAG_RETRIEVAL_DURATION = Histogram(
    "rag_retrieval_duration_seconds", "Retrieval duration"
)
RAG_LLM_DURATION = Histogram(
    "rag_llm_generation_duration_seconds", "LLM generation duration"
)
CACHE_HITS = Counter("rag_cache_hits_total", "Answer cache hits")
CACHE_MISSES = Counter("rag_cache_misses_total", "Answer cache misses")

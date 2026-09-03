from typing import List, Dict, Optional
from sqlalchemy import text
from app.db.session import sync_engine
from app.core.config import get_settings
from app.rag.ingestion import get_embedding

settings = get_settings()

def search_faq(query: str, limit: int = 3, category: Optional[str] = None) -> List[Dict]:
    """Búsqueda semántica usando similitud de coseno en PostgreSQL con pgvector."""
    query_vector = get_embedding(query)
    vector_str = "[" + ",".join(map(str, query_vector)) + "]"

    filter_clause = ""
    params = {"query_vector": vector_str, "limit": limit}
    if category:
        filter_clause = "AND category = :category"
        params["category"] = category

    sql = f"""
        SELECT id, title, category, language, content, 
               1 - (embedding <=> CAST(:query_vector AS vector)) AS similarity
        FROM faq_documents
        WHERE embedding IS NOT NULL {filter_clause}
        ORDER BY embedding <=> CAST(:query_vector AS vector)
        LIMIT :limit;
    """

    results = []
    with sync_engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        for row in rows:
            results.append({
                "id": str(row.id),
                "title": row.title,
                "category": row.category,
                "language": row.language,
                "content": row.content,
                "similarity": float(row.similarity)
            })

    return results

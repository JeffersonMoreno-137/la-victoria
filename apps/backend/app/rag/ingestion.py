import os
import sys
import re
import uuid
from typing import List, Dict

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text
from app.db.session import sync_engine, SyncSessionLocal
from app.models.entities import FAQDocument, Language
from app.core.config import get_settings

settings = get_settings()

def get_embedding(text_content: str) -> List[float]:
    """Genera embedding con OpenAI text-embedding-3-small o vector dummy para desarrollo si falta API Key."""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-proj-mock") or settings.OPENAI_API_KEY == "your-openai-api-key-here":
        # Vector dummy normalizado de dimensión 1536 para pruebas locales sin romper la base de datos
        import random
        random.seed(abs(hash(text_content)) % (10 ** 8))
        return [random.uniform(-0.05, 0.05) for _ in range(1536)]

    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text_content
    )
    return response.data[0].embedding

def chunk_markdown(file_path: str, category: str) -> List[Dict]:
    """Divide documentos Markdown en secciones estructuradas para el RAG."""
    chunks = []
    filename = os.path.basename(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Dividir por secciones de encabezado nivel 2 (##)
    sections = re.split(r'\n(?=##\s+)', content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        first_line = section.split("\n")[0].replace("##", "").strip()
        title = first_line if first_line else filename

        # Detección de idioma del fragmento
        is_english = "english" in title.lower() or "faq (english" in title.lower()
        lang = Language.EN if is_english else Language.ES

        chunks.append({
            "title": title,
            "source_file": filename,
            "category": category,
            "language": lang,
            "content": section
        })

    return chunks

def ingest_knowledge_base():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../packages/knowledge-base"))
    print(f"Indexando base de conocimientos desde: {base_dir}")

    files = [
        ("itin_faq.md", "ITIN"),
        ("immigration_services.md", "IMMIGRATION")
    ]

    all_chunks = []
    for file_name, category in files:
        full_path = os.path.join(base_dir, file_name)
        if os.path.exists(full_path):
            chunks = chunk_markdown(full_path, category)
            all_chunks.extend(chunks)
            print(f"-> Procesado {file_name}: {len(chunks)} secciones extraídas.")
        else:
            print(f"Alerta: No se encontró {full_path}")

    session = SyncSessionLocal()
    try:
        # Limpiar documentos anteriores para evitar duplicados en re-ingesta
        session.query(FAQDocument).delete()
        session.commit()

        for c in all_chunks:
            embedding = get_embedding(c["content"])
            doc = FAQDocument(
                id=uuid.uuid4(),
                title=c["title"],
                source_file=c["source_file"],
                category=c["category"],
                language=c["language"],
                content=c["content"],
                embedding=embedding
            )
            session.add(doc)

        session.commit()
        print(f"Ingesta RAG completada con éxito. {len(all_chunks)} documentos vectorizados en pgvector.")
    except Exception as e:
        session.rollback()
        print(f"Error durante la ingesta vectorial: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    ingest_knowledge_base()

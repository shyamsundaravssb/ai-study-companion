import fitz
import os
import logging
from sqlalchemy.orm import Session
from app.models.material import Material, MaterialStatus
from app.models.material_chunk import MaterialChunk
from app.services import storage_service
from app.ai.providers import embedding_provider
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

def process_material(db: Session, material_id: str):
    logger.info(f"Processing material {material_id}")
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise ValueError(f"Material {material_id} not found")
        
    material.status = MaterialStatus.processing
    db.commit()
    
    temp_pdf_path = None
    try:
        # Idempotency: delete existing chunks if retrying
        db.query(MaterialChunk).filter_by(material_id=material.id).delete()
        db.commit()

        # Download from storage
        temp_pdf_path = storage_service.download_material_to_tempfile(material.storage_path)
        
        # Extract text per page and track character offsets
        doc = fitz.open(temp_pdf_path)
        material.page_count = len(doc)
        
        full_text = ""
        page_offsets = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text:
                start_idx = len(full_text)
                full_text += text
                end_idx = len(full_text)
                page_offsets.append({
                    "start": start_idx,
                    "end": end_idx,
                    "page_number": page_num + 1
                })
                
        doc.close()
        
        # Chunk text globally across the entire document
        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=800,
            chunk_overlap=100
        )
        
        chunks_to_insert = []
        chunk_idx = 0
        
        if full_text.strip():
            text_chunks = splitter.split_text(full_text)
            
            search_start = 0
            for tc in text_chunks:
                tc_stripped = tc.strip()
                if not tc_stripped:
                    continue
                    
                pos = full_text.find(tc, search_start)
                if pos == -1:
                    pos = full_text.find(tc)
                    if pos == -1:
                        pos = search_start
                        
                # Advance search_start safely accounting for overlap
                search_start = max(0, pos + len(tc) // 2)
                
                chunk_page = 1
                for po in page_offsets:
                    if po["start"] <= pos < po["end"]:
                        chunk_page = po["page_number"]
                        break
                        
                chunks_to_insert.append({
                    "chunk_index": chunk_idx,
                    "page_number": chunk_page,
                    "content": tc_stripped
                })
                chunk_idx += 1
                
        # Embed and store
        if chunks_to_insert:
            batch_size = 96
            all_embeddings = []
            texts = [c["content"] for c in chunks_to_insert]
            
            batches = 0
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                logger.info(f"Embedding batch of {len(batch_texts)} chunks...")
                batch_embeddings = embedding_provider.embed_documents(batch_texts)
                all_embeddings.extend(batch_embeddings)
                batches += 1
                
            logger.info(f"{len(texts)} chunks embedded in {batches} batch calls of <=96 each.")
            
            db_chunks = []
            for i, c in enumerate(chunks_to_insert):
                embedding = all_embeddings[i]
                assert len(embedding) == 1536, f"Expected 1536 dims, got {len(embedding)}"
                
                db_chunks.append(MaterialChunk(
                    material_id=material.id,
                    project_id=material.project_id,
                    chunk_index=c["chunk_index"],
                    page_number=c["page_number"],
                    content=c["content"],
                    embedding=embedding
                ))
                
            db.bulk_save_objects(db_chunks)
            
        material.status = MaterialStatus.ready
        db.commit()
        logger.info(f"Successfully processed material {material_id}")
        
    except Exception as e:
        logger.error(f"Failed to process material {material_id}: {e}")
        material.status = MaterialStatus.failed
        db.commit()
        raise e
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

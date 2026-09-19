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
                # FIX 2: Sanitize extracted PDF text by removing NUL bytes
                text = text.replace('\x00', '')
                
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
                batch_embeddings = embedding_provider.embed_document(batch_texts, project_id=material.project_id)
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
            
        # --- Concept Extraction (One-off per material ingestion) ---
        try:
            import asyncio
            from app.ai.concept_extraction import extract_concepts
            from app.models.concept import Concept
            
            # Strategy: take up to the first 8 chunks (~6k chars max) to avoid blowing up context window
            # and to stay safely under the Groq free tier 8000 TPM limit, while still giving the LLM a 
            # solid grasp of the core concepts in the material.
            sampled_texts = [c["content"] for c in chunks_to_insert[:8]]
            chunks_text = "\n\n".join(sampled_texts)
            
            if chunks_text.strip():
                logger.info("Extracting concepts from material...")
                extracted = asyncio.run(extract_concepts(material.project_id, chunks_text))
                
                # Idempotency guard: exact name collision check within the project
                existing_concepts = db.query(Concept).filter_by(project_id=material.project_id).all()
                existing_names = {c.name.lower().strip() for c in existing_concepts}
                
                new_db_concepts = []
                for ec in extracted.concepts:
                    clean_name = ec.name.strip()
                    if clean_name.lower() not in existing_names:
                        new_db_concepts.append(Concept(
                            project_id=material.project_id,
                            name=clean_name,
                            description=ec.description.strip()
                        ))
                        existing_names.add(clean_name.lower())
                
                if new_db_concepts:
                    db.bulk_save_objects(new_db_concepts)
                    logger.info(f"Inserted {len(new_db_concepts)} new concepts for project {material.project_id}")
                else:
                    logger.info("No new concepts inserted (all were exact name collisions).")
        except Exception as ce:
            # Note: deliberate failure isolation. Do not fail the whole ingestion if concept extraction fails.
            logger.error(f"Concept extraction failed for material {material_id}: {ce}")
        # -----------------------------------------------------------

            
        material.status = MaterialStatus.ready
        material.error = None
        db.commit()
        logger.info(f"Successfully processed material {material_id}")
        
    except Exception as e:
        logger.error(f"Failed to process material {material_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        
        material = db.query(Material).filter_by(id=material_id).first()
        if material:
            material.status = MaterialStatus.failed
            material.error = str(e)[:1000]
            db.commit()
            
        raise e
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

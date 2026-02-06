"""
Knowledge Base Indexing Script
Run this script to index all knowledge documents into the vector database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Main function to index the knowledge base."""
    print("=" * 60)
    print("Knowledge Base Indexing Tool")
    print("=" * 60)
    
    try:
        # Import GenAI modules
        from modules.genai.embedding_service import EmbeddingService
        from modules.genai.vector_store import VectorStore
        from modules.genai.document_search import DocumentSearch
        
        print("\n1. Initializing services...")
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        document_search = DocumentSearch(embedding_service, vector_store)
        
        # Check documents path
        docs_path = document_search.documents_path
        print(f"\n2. Documents path: {docs_path}")
        
        if not os.path.exists(docs_path):
            print(f"   Creating directory: {docs_path}")
            os.makedirs(docs_path, exist_ok=True)
        
        # List documents
        files = []
        for root, dirs, filenames in os.walk(docs_path):
            for f in filenames:
                if any(f.endswith(ext) for ext in ['.txt', '.md', '.pdf', '.docx']):
                    files.append(os.path.join(root, f))
        
        print(f"\n3. Found {len(files)} documents to index:")
        for f in files:
            print(f"   - {os.path.basename(f)}")
        
        if not files:
            print("\n   No documents found. Add documents to the knowledge_base/documents folder.")
            return
        
        # Index documents
        print("\n4. Indexing documents...")
        document_search.load_and_index_documents()
        
        # Show stats
        stats = vector_store.get_collection_stats()
        print(f"\n5. Indexing complete!")
        print(f"   - Document chunks indexed: {stats.get('document_count', 0)}")
        print(f"   - Defects indexed: {stats.get('defect_count', 0)}")
        
        print("\n" + "=" * 60)
        print("Knowledge base ready for AI search!")
        print("=" * 60)
        
    except ImportError as e:
        print(f"\nError: Missing required packages. {e}")
        print("Run: pip install sentence-transformers chromadb")
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()

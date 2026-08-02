import chromadb
from config import COLLECTION_NAME, RESOLVED_CHROMA_DB_PATH

# Connect to ChromaDB
client = chromadb.PersistentClient(path=RESOLVED_CHROMA_DB_PATH)
print(f"Using ChromaDB at: {RESOLVED_CHROMA_DB_PATH}")

# Get the collection
try:
    collection = client.get_collection(name=COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' found!")
    print(f"Total vectors in collection: {collection.count()}")
    
    # Get all documents and their metadata
    all_data = collection.get(include=['documents', 'metadatas'])
    
    print("\nFirst 5 chunks (to check content):")
    print("=" * 80)
    for i in range(min(5, len(all_data['documents']))):
        doc = all_data['documents'][i]
        meta = all_data['metadatas'][i]
        print(f"\nChunk {i+1}:")
        print(f"Source: {meta.get('source', 'unknown')}")
        print(f"Content preview: {doc[:200]}...")
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"Error: {e}")

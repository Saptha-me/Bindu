import os
import re

class EvidenceRetriever:
    def __init__(self, guidelines_dir):
        self.guidelines_dir = guidelines_dir
        self.guidelines = self._load_guidelines()

    def _load_guidelines(self):
        guidelines = []
        if not os.path.exists(self.guidelines_dir):
            return guidelines
        
        for filename in os.listdir(self.guidelines_dir):
            if filename.endswith(".txt"):
                path = os.path.join(self.guidelines_dir, filename)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Basic metadata extraction
                    protocol_id = "UNKNOWN"
                    title = filename
                    
                    id_match = re.search(r"institutional_protocol:\s*(\S+)", content)
                    if id_match:
                        protocol_id = id_match.group(1)
                    
                    title_match = re.search(r"Title:\s*(.+)", content)
                    if title_match:
                        title = title_match.group(1).strip()
                    
                    guidelines.append({
                        "id": protocol_id,
                        "title": title,
                        "content": content,
                        "filename": filename
                    })
        return guidelines

    def retrieve(self, query):
        """
        Simple keyword-based retrieval as a fallback/simplified RAG.
        Returns a list of matching snippets and their sources.
        """
        matches = []
        query_words = set(re.findall(r'\w+', query.lower()))
        
        for g in self.guidelines:
            # Score based on keyword overlap
            content_lower = g["content"].lower()
            score = 0
            for word in query_words:
                if len(word) > 3 and word in content_lower:
                    score += 1
            
            if score > 0:
                # Extract relevant section (simplified: return first 500 chars)
                # In a real RAG, we'd use embeddings and chunking.
                matches.append({
                    "source": g["id"],
                    "title": g["title"],
                    "relevance_score": score,
                    "snippet": g["content"][:1000] # Provide full content if small
                })
        
        # Sort by relevance
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches

if __name__ == "__main__":
    # Test retriever
    retriever = EvidenceRetriever("guidelines")
    results = retriever.retrieve("What is the first line treatment for hypertension?")
    for r in results:
        print(f"Source: {r['source']} ({r['title']})")
        print(f"Snippet: {r['snippet'][:100]}...")

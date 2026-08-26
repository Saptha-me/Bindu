import os
import re
import json

class EvidenceRetriever:
    def __init__(self, guidelines_dir="guidelines"):
        self.guidelines_dir = guidelines_dir
        self.guidelines = self._load_guidelines()
        self.therapeutic_assets = self._load_therapeutic_assets()

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
                    
                    id_match = re.search(r"ID:\s*(\S+)", content)
                    if not id_match:
                        id_match = re.search(r"institutional_protocol:\s*(\S+)", content)
                    
                    if id_match:
                        protocol_id = id_match.group(1)
                    
                    title_match = re.search(r"TITLE:\s*(.+)", content)
                    if not title_match:
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

    def _load_therapeutic_assets(self):
        path = os.path.join(os.path.dirname(__file__), "therapeutic_assets.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f).get("calming_sounds", [])
        return []

    def get_evidence(self, query):
        """
        Retrieves matching clinical evidence.
        """
        results = self.retrieve(query)
        if results:
            return {
                "source": results[0]["source"],
                "content": results[0]["snippet"],
                "therapeutic_sounds": self.get_therapeutic_sounds(query)
            }
        return None

    def get_therapeutic_sounds(self, query):
        """
        Matches calming sounds based on query keywords.
        """
        matches = []
        q = query.lower()
        for sound in self.therapeutic_assets:
            for condition in sound["recommended_for"]:
                if condition.lower() in q:
                    matches.append(sound)
                    break
        return matches

    def retrieve(self, query):
        matches = []
        query_words = set(re.findall(r'\w+', query.lower()))
        
        for g in self.guidelines:
            content_lower = g["content"].lower()
            score = 0
            for word in query_words:
                if len(word) > 3 and word in content_lower:
                    score += 1
            
            if score > 0:
                matches.append({
                    "source": g["id"],
                    "title": g["title"],
                    "relevance_score": score,
                    "snippet": g["content"]
                })
        
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches

if __name__ == "__main__":
    # Test retriever
    retriever = EvidenceRetriever("guidelines")
    results = retriever.retrieve("What is the first line treatment for hypertension?")
    for r in results:
        print(f"Source: {r['source']} ({r['title']})")
        print(f"Snippet: {r['snippet'][:100]}...")

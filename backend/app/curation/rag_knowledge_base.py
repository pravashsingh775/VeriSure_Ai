import json
from pathlib import Path
from typing import Any


class PackagingRAGKnowledgeBase:
    """
    RAG Knowledge Base for Amul packaging specifications and regulatory context.
    IMPORTANT: Provides contextual domain knowledge and NEVER overrides measured CV/ML evidence.
    """

    DISCLAIMER = (
        "RAG contextual specifications represent documented regulatory & factory standards. "
        "They provide semantic context and NEVER override empirical visual or computer vision measurements."
    )

    def __init__(self, knowledge_dir: Path | None = None):
        if knowledge_dir is None:
            self.knowledge_dir = Path(r"C:\Users\PRAVASH\Desktop\VeriSure_Ai\data\rag_knowledge")
        else:
            self.knowledge_dir = Path(knowledge_dir)

        self.documents: dict[str, dict[str, Any]] = {}
        self._load_knowledge()

    def _load_knowledge(self) -> None:
        """Loads all JSON specification documents in knowledge_dir."""
        if not self.knowledge_dir.exists():
            return

        for filepath in self.knowledge_dir.glob("*.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    doc_id = filepath.stem
                    self.documents[doc_id] = data
            except Exception:
                pass

    def query_product_spec(self, variant: str) -> dict[str, Any]:
        """
        Retrieves official documented packaging parameters for a given variant.
        """
        v_upper = variant.upper()
        if "GOLD" in v_upper:
            doc = self.documents.get("amul_gold_specification", {})
        elif "TAAZA" in v_upper:
            doc = self.documents.get("amul_taaza_specification", {})
        elif "SHAKTI" in v_upper:
            doc = self.documents.get("amul_shakti_specification", {})
        else:
            doc = {}

        return {
            "variant": variant,
            "specification": doc,
            "disclaimer": self.DISCLAIMER
        }

    def query_regulatory_requirements(self) -> dict[str, Any]:
        """
        Retrieves FSSAI and Legal Metrology packaging declarations.
        """
        reg = self.documents.get("fssai_packaging_regulations", {})
        return {
            "regulations": reg,
            "disclaimer": self.DISCLAIMER
        }

    def get_known_packaging_versions(self, variant: str) -> list[dict[str, Any]]:
        """
        Lists officially known packaging version design iterations.
        """
        spec = self.query_product_spec(variant).get("specification", {})
        return spec.get("packaging_versions", [])

    def search_knowledge(self, query: str) -> list[dict[str, Any]]:
        """
        Keyword and topic search across the RAG knowledge corpus.
        """
        q_tokens = [w.lower() for w in query.split()]
        matches = []

        for doc_id, doc in self.documents.items():
            doc_str = json.dumps(doc).lower()
            hit_count = sum(1 for token in q_tokens if token in doc_str)
            if hit_count > 0:
                matches.append({
                    "doc_id": doc_id,
                    "title": doc.get("title", doc_id),
                    "hit_count": hit_count,
                    "snippet": doc.get("description", doc.get("title", ""))
                })

        matches.sort(key=lambda x: x["hit_count"], reverse=True)
        return matches


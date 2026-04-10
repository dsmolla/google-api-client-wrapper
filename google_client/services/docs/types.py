from dataclasses import dataclass

@dataclass
class Document:
    document_id: str
    title: str
    revision_id: str
    
    # We can omit full body content here to keep it lightweight, 
    # but agents might need it. For now we only store metadata.

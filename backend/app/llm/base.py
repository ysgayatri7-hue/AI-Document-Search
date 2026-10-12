from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class GroundedGeneration:
    answer:str
    claims:list[str]
    citation_numbers:list[int]
    provider:str

class LLMProvider(Protocol):
    def generate(self,question:str,contexts:list[dict])->GroundedGeneration: ...

class ExtractiveProvider:
    """Offline provider: quotes retrieved passages and never claims model synthesis."""
    def generate(self,question:str,contexts:list[dict])->GroundedGeneration:
        sentences=[]
        for i,context in enumerate(contexts[:3],1):
            text=" ".join(context["text"].split())[:360]
            sentences.append(f"{text} [{i}]")
        answer=" ".join(sentences) if sentences else "I could not find sufficient evidence in your indexed documents."
        return GroundedGeneration(answer=answer,claims=sentences,citation_numbers=list(range(1,len(sentences)+1)),provider="extractive")


from typing import List, Optional, Dict, Any
import re


class ModerationService:
    """Moderation service using GLiNER2 for NER-based content moderation."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from gliner import GLiNER
                self._model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
            except Exception:
                self._model = None
        return self._model

    def detect_entities(self, text: str, entity_types: List[str]) -> List[Dict[str, Any]]:
        model = self._get_model()
        if model is None:
            return []
        entities = model.predict_entities(text, entity_types, threshold=0.5)
        return [
            {"text": e["text"], "label": e["label"], "start": e["start"], "end": e["end"], "score": e["score"]}
            for e in entities
        ]

    def redact_text(self, text: str, entity_types: List[str], replacement: str = "[REDACTED]") -> str:
        entities = self.detect_entities(text, entity_types)
        entities.sort(key=lambda x: x["start"], reverse=True)
        result = text
        for entity in entities:
            label_replacement = replacement.replace("{label}", entity["label"])
            result = result[:entity["start"]] + label_replacement + result[entity["end"]:]
        return result

    def moderate_content(self, text: str, rules: list) -> Dict[str, Any]:
        results = {"original": text, "moderated": text, "entities_found": [], "blocked": False}
        for rule in rules:
            if not rule.is_active:
                continue
            entity_types = rule.entity_types or []
            if not entity_types:
                continue
            entities = self.detect_entities(text, entity_types)
            results["entities_found"].extend(entities)
            if rule.action == "block" and entities:
                results["blocked"] = True
                return results
            elif rule.action == "redact":
                replacement = rule.replacement_template or "[REDACTED]"
                results["moderated"] = self.redact_text(
                    results["moderated"], entity_types, replacement
                )
            elif rule.action == "flag":
                pass  # just flag, entities are already recorded
        return results


_moderation_service = None

def get_moderation_service() -> ModerationService:
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service

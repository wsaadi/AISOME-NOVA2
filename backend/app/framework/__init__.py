"""
AISOME NOVA2 - Agent Framework

Framework standardisé pour le développement, l'exécution et la gestion des agents IA.
Tout agent doit suivre les conventions définies dans AGENT_FRAMEWORK.md.

Architecture:
    - base/       : Classes abstraites (BaseAgent, BaseTool, BaseConnector)
    - runtime/    : Moteur d'exécution (engine, context, pipeline, session)
    - tools/      : Registre et bibliothèque de tools centralisés
    - connectors/ : Registre et bibliothèque de connecteurs centralisés
    - storage/    : Stockage MinIO cloisonné par user × agent
    - testing/    : Kit de test (MockContext, AgentTestCase)
"""

__version__ = "1.0.0"

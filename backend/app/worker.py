"""
Celery Worker — Configuration de Celery pour l'exécution asynchrone des agents.

Les agents sont exécutés par des workers Celery, pas par le serveur API.
Cela permet:
- L'utilisateur n'attend pas (le job tourne en arrière-plan)
- Plusieurs agents en parallèle
- Scale horizontal (ajouter des workers)
- L'utilisateur peut naviguer ailleurs et revenir voir le résultat

Architecture:
    API → Redis (broker) → Celery Worker → Agent.handle_message()
    Worker → Redis (pub/sub) → WebSocket → Frontend (progression temps réel)
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

# Configuration Celery
celery_app = Celery(
    "nova2",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
)

celery_app.conf.update(
    # Sérialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Résultats
    result_expires=3600,  # 1h
    # Concurrence
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Queues
    task_default_queue="agents",
    task_routes={
        "app.tasks.agent_tasks.execute_agent_task": {"queue": "agents"},
        "app.tasks.agent_tasks.execute_agent_stream_task": {"queue": "agents"},
    },
)

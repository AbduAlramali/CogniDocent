from celery import Celery
from celery.signals import worker_process_init
from src.core.config import get_celery_settings
from kombu import Exchange, Queue

celery_app = Celery("cognidocent_backend")

# Define the main exchange and queue for backend
main_exchange = Exchange("main_exchange", type="topic")
backend_queue = Queue(
    "backend_queue",
    exchange=main_exchange,
    routing_key="backend.#",
)

# Merge settings from config with manual overrides
conf = get_celery_settings().model_dump()
conf.update(
    {
        "task_queues": (backend_queue,),
        "task_default_queue": "backend_queue",
        "task_default_exchange": main_exchange.name,
        "task_default_exchange_type": main_exchange.type,
        "task_default_routing_key": "backend.report_success",
    }
)

celery_app.conf.update(conf)

# Auto-discover tasks in your listeners file
celery_app.conf.imports = ["app.infra.listeners"]


@worker_process_init.connect
def bootstrap_worker_instance(*args, **kwargs):
    # 1. Dispose of the inherited engine pool so that the child process recreates it
    try:
        from src.infra.postgres_adapter import engine

        engine.sync_engine.dispose()
    except Exception:
        # Prevent task failures if there's any import/dispose error during bootstrap
        pass

    # 2. Initialize S3 client for worker context
    try:
        from src.core.config import get_minio_settings, get_app_settings
        from src.infra.clients import minio_client

        minio_settings = get_minio_settings()
        app_settings = get_app_settings()
        minio_client.initialize(minio_settings, app_settings)
    except Exception:
        pass

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from config import settings
from bitrix24.client import Bitrix24Client
from monitoring.service import MonitoringService
from monitoring.logger_handler import log_deal_event
from api.routes import router, set_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

client: Bitrix24Client | None = None
service: MonitoringService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, service

    client = Bitrix24Client(settings.bitrix24_webhook_url)
    service = MonitoringService(
        client=client,
        poll_interval=settings.poll_interval_seconds,
        stages_filter=settings.stages_filter or None,
        assigned_filter=settings.assigned_filter or None,
    )
    service.add_handler(log_deal_event)
    set_service(service)

    await service.start()
    logger.info("Bitrix24 monitoring service started")
    logger.info("Web interface: http://%s:%d", settings.host, settings.port)
    logger.info("API docs:      http://%s:%d/docs", settings.host, settings.port)

    yield

    await service.stop()
    await client.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Bitrix24 Deal Monitor",
    description="Сервис мониторинга сделок Bitrix24",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )

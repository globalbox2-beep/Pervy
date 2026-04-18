import asyncio
import logging
from datetime import datetime
from typing import Callable, Awaitable

from bitrix24.client import Bitrix24Client, BitrixError
from bitrix24.deals import Deal, DealsApi

logger = logging.getLogger(__name__)

DealEventHandler = Callable[[str, Deal, Deal | None], Awaitable[None]]


class MonitoringService:
    """Polls Bitrix24 for deal changes and fires events on new/modified deals."""

    def __init__(
        self,
        client: Bitrix24Client,
        poll_interval: int = 60,
        stages_filter: list[str] | None = None,
        assigned_filter: list[str] | None = None,
    ):
        self._api = DealsApi(client)
        self._interval = poll_interval
        self._stages = stages_filter or []
        self._assigned = assigned_filter or []
        self._known_deals: dict[str, Deal] = {}
        self._handlers: list[DealEventHandler] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self.last_poll: datetime | None = None
        self.last_error: str | None = None
        self.total_polls: int = 0

    def add_handler(self, handler: DealEventHandler):
        self._handlers.append(handler)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Monitoring started (interval=%ds)", self._interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring stopped")

    async def _poll_loop(self):
        while self._running:
            try:
                await self._poll()
            except Exception as e:
                self.last_error = str(e)
                logger.error("Poll error: %s", e)
            await asyncio.sleep(self._interval)

    async def _poll(self):
        deals = await self._api.list_deals(
            stages=self._stages or None,
            assigned_ids=self._assigned or None,
        )
        self.last_poll = datetime.now()
        self.total_polls += 1
        self.last_error = None

        current_ids = {d.id for d in deals}

        for deal in deals:
            previous = self._known_deals.get(deal.id)
            if previous is None:
                event = "created"
            elif deal.date_modify > previous.date_modify:
                event = "updated"
            else:
                continue
            self._known_deals[deal.id] = deal
            await self._fire(event, deal, previous)

        # deals that disappeared (closed/deleted externally)
        removed_ids = set(self._known_deals) - current_ids
        for rid in removed_ids:
            old = self._known_deals.pop(rid)
            await self._fire("removed", old, None)

        logger.info("Poll complete: %d deals tracked", len(self._known_deals))

    async def _fire(self, event: str, deal: Deal, previous: Deal | None):
        logger.debug("Event %s for deal #%s '%s'", event, deal.id, deal.title)
        for handler in self._handlers:
            try:
                await handler(event, deal, previous)
            except Exception as e:
                logger.error("Handler error on event %s: %s", event, e)

    def snapshot(self) -> list[Deal]:
        return list(self._known_deals.values())

    def stats(self) -> dict:
        deals = self.snapshot()
        by_stage: dict[str, int] = {}
        total_amount = 0.0
        for d in deals:
            by_stage[d.stage_id] = by_stage.get(d.stage_id, 0) + 1
            total_amount += d.opportunity
        return {
            "total_deals": len(deals),
            "by_stage": by_stage,
            "total_amount": round(total_amount, 2),
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
            "last_error": self.last_error,
            "total_polls": self.total_polls,
            "is_running": self._running,
        }

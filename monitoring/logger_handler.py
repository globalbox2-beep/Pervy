import logging
from bitrix24.deals import Deal

logger = logging.getLogger("deals.events")


async def log_deal_event(event: str, deal: Deal, previous: Deal | None):
    """Default handler: logs deal events to stdout."""
    if event == "created":
        logger.info(
            "[NEW DEAL] #%s '%s' | Stage: %s | Amount: %.2f %s",
            deal.id, deal.title, deal.stage_id, deal.opportunity, deal.currency_id,
        )
    elif event == "updated":
        changes = []
        if previous and previous.stage_id != deal.stage_id:
            changes.append(f"stage: {previous.stage_id} → {deal.stage_id}")
        if previous and previous.opportunity != deal.opportunity:
            changes.append(f"amount: {previous.opportunity} → {deal.opportunity}")
        if previous and previous.assigned_by_id != deal.assigned_by_id:
            changes.append(f"assigned: {previous.assigned_by_id} → {deal.assigned_by_id}")
        changes_str = ", ".join(changes) if changes else "modified"
        logger.info(
            "[UPDATED] #%s '%s' | %s",
            deal.id, deal.title, changes_str,
        )
    elif event == "removed":
        logger.info("[REMOVED] #%s '%s'", deal.id, deal.title)

import logging
import httpx
from bitrix24.deals import Deal

logger = logging.getLogger(__name__)

_STAGE_LABELS: dict[str, str] = {
    "NEW": "Новая",
    "PREPARATION": "Подготовка",
    "EXECUTING": "В работе",
    "FINAL_INVOICE": "Финальный счёт",
    "WON": "Выиграна",
    "LOSE": "Проиграна",
}


def _stage_label(stage_id: str) -> str:
    return _STAGE_LABELS.get(stage_id, stage_id)


def _fmt_amount(amount: float, currency: str) -> str:
    return f"{amount:,.0f} {currency}".replace(",", " ")


def _build_message(event: str, deal: Deal, previous: Deal | None) -> str:
    link = f"https://t.me/share"  # placeholder; real link built per-domain
    if event == "created":
        return (
            f"🟢 *Новая сделка #{deal.id}*\n"
            f"📌 {deal.title}\n"
            f"💰 {_fmt_amount(deal.opportunity, deal.currency_id)}\n"
            f"📊 Стадия: {_stage_label(deal.stage_id)}\n"
            f"👤 Ответственный: {deal.assigned_by_id}"
        )
    elif event == "updated":
        lines = [f"✏️ *Изменена сделка #{deal.id}*", f"📌 {deal.title}"]
        if previous and previous.stage_id != deal.stage_id:
            lines.append(
                f"📊 Стадия: {_stage_label(previous.stage_id)} → {_stage_label(deal.stage_id)}"
            )
        if previous and previous.opportunity != deal.opportunity:
            lines.append(
                f"💰 Сумма: {_fmt_amount(previous.opportunity, previous.currency_id)}"
                f" → {_fmt_amount(deal.opportunity, deal.currency_id)}"
            )
        if previous and previous.assigned_by_id != deal.assigned_by_id:
            lines.append(
                f"👤 Ответственный: {previous.assigned_by_id} → {deal.assigned_by_id}"
            )
        if len(lines) == 2:
            lines.append("_(другие изменения)_")
        return "\n".join(lines)
    elif event == "removed":
        return (
            f"🔴 *Сделка #{deal.id} закрыта/удалена*\n"
            f"📌 {deal.title}\n"
            f"💰 {_fmt_amount(deal.opportunity, deal.currency_id)}"
        )
    return ""


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, notify_events: list[str] | None = None):
        self._token = bot_token
        self._chat_id = chat_id
        self._notify_events = set(notify_events or ["created", "updated", "removed"])
        self._api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async def __call__(self, event: str, deal: Deal, previous: Deal | None):
        if event not in self._notify_events:
            return
        text = _build_message(event, deal, previous)
        if not text:
            return
        await self._send(text)

    async def _send(self, text: str):
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self._api_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Telegram send error: %s", e)

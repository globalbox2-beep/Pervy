from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .client import Bitrix24Client


@dataclass
class Deal:
    id: str
    title: str
    stage_id: str
    opportunity: float
    currency_id: str
    assigned_by_id: str
    date_create: datetime
    date_modify: datetime
    closed: bool
    company_id: Optional[str] = None
    contact_id: Optional[str] = None
    comment: Optional[str] = None
    additional_info: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "Deal":
        return cls(
            id=data["ID"],
            title=data.get("TITLE", ""),
            stage_id=data.get("STAGE_ID", ""),
            opportunity=float(data.get("OPPORTUNITY") or 0),
            currency_id=data.get("CURRENCY_ID", "RUB"),
            assigned_by_id=data.get("ASSIGNED_BY_ID", ""),
            date_create=_parse_dt(data.get("DATE_CREATE")),
            date_modify=_parse_dt(data.get("DATE_MODIFY")),
            closed=data.get("CLOSED") == "Y",
            company_id=data.get("COMPANY_ID") or None,
            contact_id=data.get("CONTACT_ID") or None,
            comment=data.get("COMMENTS") or None,
            additional_info={k: v for k, v in data.items()
                             if k not in _KNOWN_FIELDS and v not in (None, "", "0")},
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "stage_id": self.stage_id,
            "opportunity": self.opportunity,
            "currency_id": self.currency_id,
            "assigned_by_id": self.assigned_by_id,
            "date_create": self.date_create.isoformat(),
            "date_modify": self.date_modify.isoformat(),
            "closed": self.closed,
            "company_id": self.company_id,
            "contact_id": self.contact_id,
            "comment": self.comment,
        }


_KNOWN_FIELDS = {
    "ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID",
    "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSED",
    "COMPANY_ID", "CONTACT_ID", "COMMENTS",
}


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.min
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt.replace("%z", ""))
        except ValueError:
            continue
    return datetime.min


DEAL_SELECT_FIELDS = [
    "ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID",
    "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY", "CLOSED",
    "COMPANY_ID", "CONTACT_ID", "COMMENTS",
]


class DealsApi:
    def __init__(self, client: Bitrix24Client):
        self._client = client

    async def list_deals(
        self,
        stages: list[str] | None = None,
        assigned_ids: list[str] | None = None,
        modified_after: datetime | None = None,
    ) -> list[Deal]:
        filter_params: dict = {}
        if stages:
            filter_params["STAGE_ID"] = stages
        if assigned_ids:
            filter_params["ASSIGNED_BY_ID"] = assigned_ids
        if modified_after:
            filter_params[">DATE_MODIFY"] = modified_after.strftime("%Y-%m-%dT%H:%M:%S")

        raw = await self._client.list_all(
            "crm.deal.list",
            {"select": DEAL_SELECT_FIELDS, "filter": filter_params, "order": {"DATE_MODIFY": "DESC"}},
        )
        return [Deal.from_api(item) for item in raw]

    async def get_deal(self, deal_id: str) -> Deal:
        raw = await self._client.call("crm.deal.get", {"id": deal_id})
        return Deal.from_api(raw)

    async def get_stages(self) -> list[dict]:
        raw = await self._client.call("crm.dealcategory.stage.list", {"id": 0})
        return raw or []

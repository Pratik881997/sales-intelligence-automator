from pydantic import BaseModel, Field


class SectionItem(BaseModel):
    """Dynamic section in the sales brief (title + body from available site evidence)."""

    title: str = ""
    content: str = ""


class SalesBrief(BaseModel):
    lead_input: str
    resolved_url: str = ""
    company_name: str = ""
    # Flat summaries (often mirrored from key sections for exports / legacy use).
    company_overview: str = ""
    core_product_or_service: str = ""
    target_customer_or_audience: str = ""
    contact_details: str = ""
    services_offered: str = ""
    # Ordered, dynamic sections — only include when supported by crawled content.
    sections: list[SectionItem] = Field(default_factory=list)
    b2b_qualified: bool = False
    b2b_confidence: int = Field(default=0, ge=0, le=100)
    sales_questions: list[str] = Field(default_factory=list)
    rationale: str = ""
    signals: list[str] = Field(default_factory=list)
    research_notes: str = ""

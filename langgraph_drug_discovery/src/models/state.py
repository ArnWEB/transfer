from typing import Optional, TypedDict


class SummaryState(TypedDict):
    user_input: str
    disease_name: Optional[str]
    raw_response: Optional[dict]
    summary_markdown: Optional[str] 
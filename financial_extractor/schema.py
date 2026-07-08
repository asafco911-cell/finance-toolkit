from pydantic import BaseModel, Field

class EarningsData(BaseModel):
    revenue: float = Field(description="Total revenue in USD, as a number")
    net_income: float = Field(description="Net income/profit in USD, as a number")
    eps: float = Field(description="Earnings per share, as a number")
    guidance: str = Field(description="Company's forward guidance: raised, lowered, maintained, or not mentioned")
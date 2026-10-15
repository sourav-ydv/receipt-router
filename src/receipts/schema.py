from pydantic import BaseModel, Field


class LineItem(BaseModel):
    name: str
    quantity: int = 1
    price: float
    discount: float = 0.0


class Receipt(BaseModel):
    items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = None
    discount: float | None = None
    service: float | None = None
    tax: float | None = None
    total: float | None = None

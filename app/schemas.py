from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    name: str
    barcode: str | None = None
    unit_cost: Decimal = 0
    sale_price: Decimal = 0
    reorder_level: int = 0

class ProductOut(ProductIn):
    id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)

class WarehouseIn(BaseModel):
    name: str
    country: str = ""

class WarehouseOut(WarehouseIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SupplierIn(BaseModel):
    name: str
    email: str | None = None
    currency: str = "USD"

class CustomerIn(BaseModel):
    name: str
    kind: str = "retail"
    email: str | None = None

class StockAdjustment(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int
    transaction_type: str = "adjustment"
    reference: str | None = None

class ImportCostIn(BaseModel):
    freight: Decimal = 0
    duty: Decimal = 0
    insurance: Decimal = 0
    other_cost: Decimal = 0

class SalesLineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)

class SalesOrderIn(BaseModel):
    customer_id: int | None = None
    channel: str = "amazon"
    external_id: str | None = None
    warehouse_id: int
    lines: list[SalesLineIn] = Field(min_length=1)

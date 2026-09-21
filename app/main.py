from decimal import Decimal
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .database import get_db, init_db
from .models import Customer, ImportShipment, InventoryTransaction, Product, SalesLine, SalesOrder, Stock, Supplier, Warehouse
from .schemas import CustomerIn, ImportCostIn, ProductIn, ProductOut, SalesOrderIn, StockAdjustment, SupplierIn, WarehouseIn, WarehouseOut

app = FastAPI(title="Import Export ERP", version="0.1.0", description="Amazon retail/wholesale inventory, purchasing and landed-cost API")

@app.on_event("startup")
def startup():
    init_db()

def get_or_404(db, model, item_id):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(404, f"{model.__name__} {item_id} not found")
    return item

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    products = db.scalar(select(func.count(Product.id))) or 0
    stock_units = db.scalar(select(func.coalesce(func.sum(Stock.quantity - Stock.reserved), 0))) or 0
    sales = db.scalar(select(func.coalesce(func.sum(SalesOrder.total), 0))) or Decimal("0")
    low_stock = db.scalar(select(func.count(Product.id)).where(Product.id.in_(select(Stock.product_id).group_by(Stock.product_id).having(func.sum(Stock.quantity - Stock.reserved) <= Product.reorder_level)))) or 0
    return {"products": products, "available_units": stock_units, "sales_value": sales, "low_stock_products": low_stock}

@app.post("/api/products", response_model=ProductOut)
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    if db.scalar(select(Product).where(Product.sku == payload.sku)):
        raise HTTPException(409, "SKU already exists")
    item = Product(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.get("/api/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return list(db.scalars(select(Product).order_by(Product.name)))

@app.get("/api/products/{product_id}", response_model=ProductOut)
def product(product_id: int, db: Session = Depends(get_db)): return get_or_404(db, Product, product_id)

@app.post("/api/warehouses", response_model=WarehouseOut)
def create_warehouse(payload: WarehouseIn, db: Session = Depends(get_db)):
    item = Warehouse(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.get("/api/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)): return list(db.scalars(select(Warehouse)))

@app.post("/api/suppliers")
def create_supplier(payload: SupplierIn, db: Session = Depends(get_db)):
    item = Supplier(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.post("/api/customers")
def create_customer(payload: CustomerIn, db: Session = Depends(get_db)):
    item = Customer(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@app.post("/api/inventory/adjust")
def adjust_inventory(payload: StockAdjustment, db: Session = Depends(get_db)):
    get_or_404(db, Product, payload.product_id); get_or_404(db, Warehouse, payload.warehouse_id)
    stock = db.scalar(select(Stock).where(Stock.product_id == payload.product_id, Stock.warehouse_id == payload.warehouse_id))
    if not stock:
        stock = Stock(product_id=payload.product_id, warehouse_id=payload.warehouse_id, quantity=0); db.add(stock)
    if stock.quantity + payload.quantity < stock.reserved:
        raise HTTPException(400, "Adjustment would make available stock negative")
    stock.quantity += payload.quantity
    db.add(InventoryTransaction(**payload.model_dump()))
    db.commit(); return {"product_id": payload.product_id, "warehouse_id": payload.warehouse_id, "quantity": stock.quantity, "available": stock.quantity - stock.reserved}

@app.get("/api/inventory")
def inventory(db: Session = Depends(get_db)):
    rows = db.scalars(select(Stock)).all()
    return [{"product_id": x.product_id, "sku": x.product.sku, "product": x.product.name, "warehouse_id": x.warehouse_id, "warehouse": x.warehouse.name, "quantity": x.quantity, "reserved": x.reserved, "available": x.quantity - x.reserved} for x in rows]

@app.post("/api/sales-orders")
def create_sales_order(payload: SalesOrderIn, db: Session = Depends(get_db)):
    total = sum((line.quantity * line.unit_price for line in payload.lines), Decimal("0"))
    order = SalesOrder(customer_id=payload.customer_id, channel=payload.channel, external_id=payload.external_id, total=total, status="confirmed")
    db.add(order); db.flush()
    for line in payload.lines:
        get_or_404(db, Product, line.product_id)
        stock = db.scalar(select(Stock).where(Stock.product_id == line.product_id, Stock.warehouse_id == payload.warehouse_id))
        if not stock or stock.quantity - stock.reserved < line.quantity: raise HTTPException(400, f"Insufficient stock for product {line.product_id}")
        stock.quantity -= line.quantity
        db.add(SalesLine(sales_order_id=order.id, product_id=line.product_id, quantity=line.quantity, unit_price=line.unit_price))
        db.add(InventoryTransaction(product_id=line.product_id, warehouse_id=payload.warehouse_id, quantity=-line.quantity, transaction_type="sale", reference=payload.external_id))
    db.commit(); db.refresh(order); return {"id": order.id, "status": order.status, "total": order.total, "channel": order.channel}

@app.post("/api/import-shipments/{shipment_id}/costs")
def update_import_costs(shipment_id: int, payload: ImportCostIn, db: Session = Depends(get_db)):
    shipment = get_or_404(db, ImportShipment, shipment_id)
    shipment.freight, shipment.duty, shipment.insurance, shipment.other_cost = payload.freight, payload.duty, payload.insurance, payload.other_cost
    db.commit()
    return {"shipment_id": shipment_id, "total_landed_cost": sum([payload.freight, payload.duty, payload.insurance, payload.other_cost])}

@app.get("/api/reorder-report")
def reorder_report(db: Session = Depends(get_db)):
    rows = db.scalars(select(Product)).all(); result=[]
    for p in rows:
        available = db.scalar(select(func.coalesce(func.sum(Stock.quantity - Stock.reserved), 0)).where(Stock.product_id == p.id)) or 0
        if available <= p.reorder_level: result.append({"sku": p.sku, "name": p.name, "available": available, "reorder_level": p.reorder_level, "suggested_quantity": max(p.reorder_level * 2 - available, 0)})
    return result

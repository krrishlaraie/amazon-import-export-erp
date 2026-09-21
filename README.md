# Amazon Import-Export ERP

A modular ERP starter for Amazon retail/wholesale import-export businesses. It covers inventory, purchasing, landed cost, sales, warehouses, suppliers, customers, and profitability in one application.

## Included in this release

- FastAPI REST API with automatic OpenAPI documentation
- Product/SKU catalog and reorder levels
- Multi-warehouse stock ledger
- Retail and wholesale sales orders
- Supplier purchase orders
- Import shipments with freight, duty, insurance, and other landed costs
- Weighted landed-cost calculation
- Dashboard metrics
- SQLite for immediate local use; PostgreSQL supported through `DATABASE_URL`
- Docker deployment

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs.

## Run with Docker

```bash
docker compose up --build
```

## API examples

```bash
curl http://localhost:8000/api/dashboard
curl -X POST http://localhost:8000/api/products -H 'Content-Type: application/json' \\
  -d '{"sku":"SKU-001","name":"Example product","unit_cost":12.50,"sale_price":29.99,"reorder_level":20}'
```

## Production roadmap

The core domain is intentionally separated so Amazon Selling Partner API, Shopify, Xero/QuickBooks, tax providers, barcode scanning, RBAC, audit logs, and background synchronization can be added without changing inventory accounting rules. Before production use, configure PostgreSQL, HTTPS, secret management, backups, authentication/RBAC, tax rules, and an accountant-reviewed chart of accounts.

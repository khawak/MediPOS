# MediPOS — Pharmacy Point of Sale System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey)
![License](https://img.shields.io/badge/License-MIT-yellow)

A comprehensive **Point of Sale & Inventory Management System** designed specifically for pharmacies and medical stores in Bangladesh. Built with Django, Bootstrap 5, and a clean modular architecture.

---

## 📋 Features by Module

### 🔐 Accounts & Authentication
- Custom user model with role-based access control (Admin, Pharmacist, Cashier)
- Login/logout with Bootstrap 5 styled forms
- Profile management with avatar upload
- Password change flow
- User CRUD (admin only)
- Role-to-group permission mapping via `setup_roles` command

### 💊 Medicines
- Category management with auto-generated slugs
- Medicine/product master with barcode, pricing, and stock tracking
- Low stock alerts with reorder levels
- Bulk CSV import/export
- Active/inactive product filtering

### 📦 Inventory
- Batch/lot tracking with expiry dates
- Stock ledger — complete audit trail of all stock movements (IN, OUT, ADJ, RET)
- Stock adjustment (positive/negative with reason)
- Expiry alerts (30-day critical, 60-day warning)
- FEFO (First Expiry First Out) stock recommendation

### 🚚 Suppliers
- Supplier/vendor management with contact details
- Active/inactive filtering
- Linked to batch and purchase modules

### 👥 Customers
- Customer database with phone as unique identifier
- Loyalty points tracking
- Purchase history (linked via sales)

### 🛒 Sales (POS)
- Full point-of-sale interface with barcode/name search
- Cart management (add, update, remove items)
- Customer selection, discount (flat & percentage), tax
- Multiple payment modes: Cash, Card, Mobile Banking, Mixed
- Auto-generated invoice numbers (INV-YYYYMMDD-XXXX)
- Sale history with search and filtering
- Invoice print (A4) and thermal (80mm) formats
- Hold & resume sale functionality

### 📊 Reports
- **Sales Summary** — KPI cards, payment breakdown, daily breakdown, PDF/Excel export
- **Profit & Loss** — Revenue vs cost per medicine with margin analysis
- **Product Sales** — Filterable by category and medicine
- **Stock Valuation** — Current inventory value at purchase price
- **Expiry Report** — Status-filtered batch expiry tracking with summary counts
- **Top Selling** — Ranked best-sellers by quantity

### ↩️ Returns
- Sales return with refund calculation
- Stock auto-restore on return
- Return reason tracking

### 📥 Purchases
- Purchase order creation and management
- Multi-item PO with unit prices and quantities
- PO status tracking (Draft, Ordered, Received, Cancelled)
- Receive PO → auto-creates batch and stock-ledger entries

### ⚙️ Settings
- Singleton shop settings (name, address, tax, currency, receipt footer)
- Database backup (create & download SQLite snapshots)
- Admin-only access controls

---

## 🧰 Tech Stack

| Category | Technology |
|----------|-----------|
| Backend | Django 4.2 |
| Frontend | Bootstrap 5.3, Bootstrap Icons |
| Forms | django-crispy-forms (Bootstrap 5) |
| Filtering | django-filter |
| PDF Export | ReportLab |
| Excel Export | openpyxl |
| Database | SQLite (dev), PostgreSQL-ready |
| Testing | pytest, pytest-django |

---

## 📦 Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Git** (optional, for cloning)

---

## 🚀 Setup Guide

### 1. Clone the Repository
```bash
git clone <repository-url>
cd medipos
```

### 2. Create a Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

### 5. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Set Up Role Groups
```bash
python manage.py setup_roles
```

### 7. Load Demo Data (Optional)
```bash
python manage.py load_demo_data
```
This creates:
- 3 users (admin, pharmacist, cashier)
- 5 medicine categories
- 10 medicines with realistic data
- 2 suppliers
- 3 customers

### 8. Create a Superuser (Alternative to demo data)
```bash
python manage.py createsuperuser
```

### 9. Run the Development Server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000**

---

## 🔑 Default Credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Administrator |
| `pharmacist` | `pharma123` | Pharmacist |
| `cashier` | `cashier123` | Cashier |

> **Note:** These are created by `load_demo_data`. For production, change passwords immediately.

---

## 📁 Project Structure

```
medipos/
├── manage.py                    # Django management script
├── conftest.py                  # Pytest configuration
├── pytest.ini                   # Pytest settings
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── README.md                    # This file
│
├── config/                      # Django project config
│   ├── settings.py              # Settings (DB, apps, auth, media)
│   ├── urls.py                  # Root URL routing
│   ├── wsgi.py                  # WSGI entry point
│   └── asgi.py                  # ASGI entry point
│
├── apps/                        # Django applications
│   ├── accounts/                # User model, auth, profile
│   │   ├── models.py            # Custom User with roles
│   │   ├── views.py             # Auth, user mgmt, DashboardView
│   │   ├── forms.py             # Login, user, profile forms
│   │   ├── signals.py           # Post-save role→group assignment
│   │   └── management/commands/
│   │       └── setup_roles.py   # Role group & permission setup
│   │
│   ├── medicines/               # Product/Category management
│   │   ├── models.py            # Category, Medicine
│   │   ├── views.py             # CRUD + CSV import
│   │   └── tests/
│   │       └── test_models.py   # Category & Medicine tests
│   │
│   ├── inventory/               # Batch & Stock Ledger
│   │   ├── models.py            # Batch, StockLedger
│   │   ├── views.py             # Batch CRUD, stock in/adj
│   │   └── tests/
│   │       └── test_models.py   # Batch & StockLedger tests
│   │
│   ├── suppliers/               # Supplier management
│   ├── customers/               # Customer database
│   │   └── tests/
│   │       └── test_models.py   # Customer tests
│   │
│   ├── sales/                   # POS & Sales
│   │   ├── models.py            # Sale, SaleItem
│   │   ├── views.py             # POS, sale list/detail, invoice
│   │   └── tests/
│   │       └── test_models.py   # Sale & SaleItem tests
│   │
│   ├── purchases/               # Purchase Orders
│   ├── returns/                 # Sales Returns
│   ├── reports/                 # Business reports (6 types)
│   ├── settings/                # Shop settings & backup
│   └── core/                    # Management commands
│       └── management/commands/
│           └── load_demo_data.py
│
├── templates/                   # HTML templates
│   ├── base.html                # Base layout (sidebar, navbar)
│   ├── dashboard.html           # Dashboard with live stats
│   ├── accounts/                # Login, profile, user mgmt
│   ├── medicines/               # Medicine & category templates
│   ├── inventory/               # Batch & stock templates
│   ├── suppliers/               # Supplier templates
│   ├── customers/               # Customer templates
│   ├── sales/                   # POS, sale list, invoice
│   ├── purchases/               # PO templates
│   ├── returns/                 # Return templates
│   ├── reports/                 # 7 report templates
│   └── settings/                # Settings & backup templates
│
├── static/                      # Static assets
│   ├── css/styles.css           # Custom CSS
│   ├── js/main.js               # Sidebar, dark mode JS
│   ├── js/pos.js                # POS interface logic
│   └── files/                   # Import templates
│
└── media/                       # User-uploaded files
    └── backups/                 # Database backups
```

---

## 🔄 Key Workflows

### POS Sale Flow
1. POS page → search/add medicines to cart
2. Select customer (optional), apply discount
3. Choose payment mode → Complete sale
4. Stock auto-deducted, invoice generated
5. Print A4 or thermal receipt

### Purchase Order Flow
1. Create PO with supplier and medicine items
2. Mark as "Ordered"
3. Receive PO → auto-creates Batch(es) and StockLedger IN entries
4. Medicine stock_quantity updated automatically via signals

### Return Flow
1. Select original sale → choose items & quantities to return
2. System calculates refund amount
3. Confirm return → stock restored, StockLedger RET entries created

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-django

# Run all tests
pytest

# Run tests for a specific app
pytest apps/medicines/tests/
pytest apps/inventory/tests/
pytest apps/customers/tests/
pytest apps/sales/tests/

# Run with verbose output
pytest -v
```

---

## 📝 License

This project is licensed under the MIT License. See the LICENSE file for details.

---

**MediPOS** — A complete pharmacy management solution built with ❤️ and Django.
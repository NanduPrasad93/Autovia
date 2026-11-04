# AutoVia – Integrated Automobile Management and Assistance System

<<<<<<< HEAD
AutoVia is a web-based automobile management and assistance platform designed to simplify vehicle ownership and automobile-related services.

The system connects vehicle owners, mechanics, workshops, spare-parts suppliers, and administrators through a centralized platform.

It helps users manage vehicle information, track maintenance records, monitor expenses, find nearby automobile services, and access essential vehicle-related assistance.

## Features

- **User Management:** Registration, login, and role-based access.
- **Vehicle Management:** Add, update, and manage vehicle details.
- **Mechanic Management:** Connect vehicle owners with mechanics.
- **Workshop Management:** Find and manage automobile service centres.
- **Spare Parts Management:** Access spare-parts supplier information.
- **Expense Tracking:** Record and monitor vehicle-related expenses.
- **Service History:** Maintain vehicle servicing and repair records.
- **Repair Estimates:** Manage repair estimates.
- **Nearby Locations:** Locate nearby fuel stations and EV charging stations using OpenStreetMap.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | Web framework |
| HTML5 | Frontend structure |
| CSS3 | Styling |
| JavaScript | Frontend functionality |
| Bootstrap 5 | Responsive UI |
| SQLite | Database |
| OpenStreetMap | Map services |
| Leaflet.js | Interactive maps |
| Chart.js | Data visualization |
| Font Awesome | Icons |

## Project Structure

```text
AutoVia/
│
├── config/             # Django project configuration
│
├── accounts/           # User authentication and profiles
├── vehicles/           # Vehicle management
├── mechanics/          # Mechanic management
├── workshops/          # Workshop management
├── suppliers/          # Spare-parts suppliers
├── expenses/           # Expense tracking
├── locations/          # Fuel stations and EV locations
├── services/           # Vehicle service records
├── core/               # Main application functionality
│
├── templates/          # HTML templates
├── static/             # CSS, JavaScript and images
│
├── manage.py           # Django management utility
├── requirements.txt    # Python dependencies
├── db.sqlite3          # SQLite database (created after migration)
└── README.md           # Project documentation
```

*Note: The structure represents the planned project organization. Some directories may appear as development progresses.*

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/NanduPrasad93/Autovia.git
```

Navigate into the project directory:

```bash
cd Autovia
```

### 2. Install Python

Make sure Python 3.10 or later is installed.

Check your Python version:

```bash
python --version
```

If Python is not installed on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. Create a Virtual Environment

Create an isolated Python environment:

```bash
python3 -m venv venv
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

### 4. Install Dependencies

Install the required Python packages:
=======
A modern, full-stack automobile technology platform built with **Python**, **Django**, **Bootstrap 5**, **Chart.js**, and **Leaflet.js / OpenStreetMap**.

AutoVia bridges vehicle owners, certified mechanics, accredited workshops, spare parts suppliers, and administrators into an integrated ecosystem for vehicle maintenance, roadside assistance, expense tracking, and parts procurement.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Objectives](#project-objectives)
3. [Main Features](#main-features)
4. [Technology Stack](#technology-stack)
5. [Project Architecture & Structure](#project-architecture--structure)
6. [Installation Requirements](#installation-requirements)
7. [Virtual Environment Setup](#virtual-environment-setup)
8. [Dependency Installation](#dependency-installation)
9. [Database Migrations](#database-migrations)
10. [Superuser Creation](#superuser-creation)
11. [Development Server Startup](#development-server-startup)
12. [Application Access & Default URLs](#application-access--default-urls)
13. [Running Automated Tests](#running-automated-tests)
14. [Configuration & Security Notes](#configuration--security-notes)
15. [Known Limitations](#known-limitations)

---

## 1. Project Overview

AutoVia eliminates fragmented automotive service experiences by consolidating vehicle health tracking, service scheduling, provider quotation comparisons, repair invoicing, expense management, and spare parts commerce into a unified web portal.

The application follows clean architectural standards, role-based access control (RBAC), and strict object ownership isolation.

---

## 2. Project Objectives

- **Unified Automobile Lifecycle**: Centralize maintenance logs, fuel spending, and insurance records for vehicle owners.
- **Provider Digitization**: Empower freelance mechanics and commercial workshops with scheduling, repair estimates, and invoicing.
- **Supply Chain Integration**: Enable spare parts distributors to manage inventory and fulfill customer orders with atomic stock reservation.
- **Transparent Governance**: Equip administrators with accreditation controls, dispute resolution pipelines, and audit trails.
- **Location-Based Proximity**: Enable instant discovery of petrol stations, diesel points, and EV charging hubs on interactive OpenStreetMap maps.

---

## 3. Main Features

### A. Vehicle Owner Portal
- **Garage Management**: Multi-vehicle registration, odometer tracking, and mileage-based service interval alerts.
- **Provider Discovery & Booking**: Search verified mechanics and accredited workshops; book maintenance with problem descriptions.
- **Repair Oversight**: Inspect quotes/estimates, track repair milestones (`ACCEPTED` &rarr; `IN_PROGRESS` &rarr; `COMPLETED`), view invoices, and submit 5-star feedback.
- **Vehicle Expense Tracking**: Log fuel refills, servicing, repairs, spare parts, insurance, and EV charging with positive amount validation and date checking.
- **Expense Analytics Dashboard**: Interactive Chart.js visualizations including 12-month spending trends, category distributions, per-vehicle comparisons, and multi-year annual histories.
- **CSV Reports & Export**: Download filtered expenditure reports formatted for record keeping.
- **Fuel & EV Station Discovery**: Leaflet.js interactive map locating nearby petrol, diesel, and EV fast chargers with Haversine distance calculations and OpenStreetMap directions.

### B. Mechanic Portal
- **Profile & Accreditation**: Professional bio, specialization, experience years, service radius, and accreditation status.
- **Work Order Management**: Accept/reject incoming tickets, update repair progress, prepare cost quotations, and issue repair bills.
- **Reviews & Invoices**: Real-time customer ratings and billing history.

### C. Workshop / Service Centre Portal
- **Facility Management**: Service centre details, bays, address, contact hotline, and accreditation status.
- **Multi-Job Service Operations**: Incoming service requests, formal repair estimates, bay repair progress, final invoices, and business analytics.

### D. Spare Parts Supplier Portal
- **Catalog Management**: Full CRUD for automotive replacement parts with image uploads, SKU numbers, compatibility, and availability toggles.
- **Inventory Console**: Real-time stock alerts for low inventory (&le; 5 units) and critical shortages.
- **Purchase Order Fulfillment**: Multi-step order lifecycle (`PENDING` &rarr; `CONFIRMED` &rarr; `PROCESSING` &rarr; `SHIPPED` &rarr; `DELIVERED`) with atomic stock deduction and cancellation restoration.

### E. Administrator Dashboard & Governance Console
- **Platform Analytics**: Database KPIs for total users, role distributions, pending accreditations, active service tickets, and complaints.
- **User Identity Management**: Search, filter by role/status, inspect profiles, and activate/deactivate accounts with self-deactivation and superuser shields.
- **Provider Accreditation**: Approve, reject with reason, or suspend mechanics, workshops, and suppliers.
- **Operational Oversight**: Monitor platform service tickets with SLA overdue flags.
- **Dispute Adjudication**: Resolve customer complaints and record official administrative responses.
- **Tamper-Resistant Audit Logging**: Chronological activity trail recording actor, action type, target entity, and IP address.

---

## 4. Technology Stack

- **Backend**: Python 3.10+, Django 5+ / 6+ (MVT architecture)
- **Database**: SQLite (ACID-compliant with `transaction.atomic()` concurrency locks)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Font Awesome 6 Icons
- **Data Visualizations**: Chart.js (Doughnut, Bar, and Line charts)
- **Mapping & GIS**: Leaflet.js, CARTO Voyager & OpenStreetMap tiles, Overpass API, Nominatim Geocoding
- **Styling**: AutoVia Custom Theme (Primary Navy: `#101B2D`, Secondary Orange: `#F97316`, Light: `#F8FAFC`, Success: `#16A34A`)

---

## 5. Project Architecture & Structure

```
autovia/
├── manage.py
├── requirements.txt
├── config/                  # Django project root configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                # Authentication, RBAC, Profiles, Admin Dashboard, Complaints
│   ├── admin_views.py       # 15 Administrative controller views
│   ├── admin_urls.py        # /admin-dashboard/ URL routing
│   ├── decorators.py        # Role decorators (@admin_required, @vehicle_owner_required, etc.)
│   ├── models.py            # UserProfile, Complaint, ActivityLog
│   ├── tests_admin.py       # Admin dashboard test suite (14 tests)
│   ├── tests_integration.py # End-to-end integration test suite (Workflows A-E)
│   └── templates/           # Auth and admin dashboard templates
├── vehicles/                # Automobile garage registration & management
│   ├── models.py            # Vehicle model
│   └── views.py             # CRUD views
├── mechanics/               # Certified technician portal & directory
│   ├── models.py            # MechanicProfile
│   └── views.py             # Work orders, estimates, bills, reviews
├── workshops/               # Commercial service centre portal
│   ├── models.py            # Workshop facility model
│   └── views.py             # Quotations, repair bays, billing, analytics
├── suppliers/               # Spare parts distributor portal
│   ├── models.py            # SupplierProfile, SparePart, SparePartOrder, SparePartOrderItem
│   └── views.py             # Catalog, inventory, atomic order fulfillment
├── expenses/                # Running costs, analytics dashboard, and reports
│   ├── models.py            # Expense (7 categories)
│   ├── forms.py             # ExpenseForm with user ownership & date validation
│   ├── views.py             # List, Add, Edit, Delete, Analytics, CSV Export
│   └── tests.py             # 10 comprehensive expense unit tests
├── locations/               # Station discovery map & Overpass API
│   ├── views.py             # nearby_stations, stations_api (caching, Haversine distance)
│   └── tests.py             # 10 locations unit tests
├── services/                # Service requests, repair bills, feedback, and history
│   ├── models.py            # ServiceRequest, RepairEstimate, RepairBill, ServiceFeedback, ServiceRecord
│   └── views.py             # Request creation, billing, feedback
└── core/                    # Public landing pages
    ├── models.py            # ContactMessage
    └── views.py             # Home, About, Services, Contact
```

---

## 6. Installation Requirements

- **Operating System**: Linux (Ubuntu, Debian, Fedora, Arch, CentOS) or macOS / WSL2
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14
- **Package Manager**: `pip` and `python3-venv`

---

## 7. Virtual Environment Setup

From the root project directory:

```bash
# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

---

## 8. Dependency Installation

Install the required packages within the active virtual environment:
>>>>>>> 6848f4c (k)

```bash
pip install -r requirements.txt
```

<<<<<<< HEAD
If `requirements.txt` has not yet been created, install Django first:

```bash
pip install "Django>=5.2,<5.3"
```

You can generate the dependency file using:

```bash
pip freeze > requirements.txt
```

### 5. Apply Database Migrations

Run the following commands:

```bash
python manage.py makemigrations
python manage.py migrate
```

This creates the required database tables using SQLite.

### 6. Create an Administrator Account

Create a superuser to access the Django administration panel:
=======
---

## 9. Database Migrations

Apply all schema migrations to generate database tables:

```bash
python manage.py migrate
```

---

## 10. Superuser Creation

Create an initial administrator account:
>>>>>>> 6848f4c (k)

```bash
python manage.py createsuperuser
```

<<<<<<< HEAD
Follow the instructions to enter your username, email, and password.

### 7. Run the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

The application will be available at:

**Main Application:**
http://127.0.0.1:8000/

**Django Administration:**
http://127.0.0.1:8000/admin/

## Usage

1. Open the application in your browser.
2. Register or log in to your account.
3. Access the dashboard.
4. Add and manage vehicle information.
5. Explore automobile services and workshops.
6. Track vehicle expenses and service history.
7. Explore nearby fuel stations and EV charging stations.

## Database

AutoVia uses SQLite as its development database.

The database file is:

```text
db.sqlite3
```

Django ORM is used to interact with the database.

## Maps and Location Services

AutoVia integrates:

- OpenStreetMap for map data.
- Leaflet.js for interactive map rendering.

These technologies support locating nearby fuel stations and electric vehicle charging stations.

## Development

To stop the development server:

```bash
CTRL + C
```

To deactivate the virtual environment:

```bash
deactivate
```

Whenever you make changes to Django models, run:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Future Enhancements

- Online service appointment booking.
- Real-time service status tracking.
- Automated vehicle maintenance reminders.
- Online spare-parts ordering.
- Advanced expense analytics.
- Integration with additional EV charging networks.

## License

This project is developed for educational and academic purposes.

---

**AutoVia – Your Vehicle, Your Services, One Platform.**
=======
Follow the interactive prompts to specify a username, email, and password. Staff and superuser status are automatically granted, allowing access to `/admin-dashboard/`.

---

## 11. Development Server Startup

Run the Django WSGI development server:

```bash
python manage.py runserver 127.0.0.1:8000
```

The server will be reachable at `http://127.0.0.1:8000/`.

---

## 12. Application Access & Default URLs

| Area | URL Route | Access Level | Description |
| :--- | :--- | :--- | :--- |
| **Public Homepage** | `/` | Public | Overview of platform features and service highlights |
| **Login** | `/accounts/login/` | Public | Authenticate with username or email |
| **Register** | `/accounts/register/` | Public | Account creation with role selection |
| **Vehicle Owner Dashboard** | `/accounts/dashboard/vehicle-owner/` | Vehicle Owner | Garage metrics, maintenance alerts, recent tickets |
| **My Vehicles** | `/vehicles/` | Vehicle Owner | Vehicle list, add, edit, and odometer logs |
| **Vehicle Expenses** | `/expenses/` | Vehicle Owner | Expense log, multi-criteria filtering, search |
| **Expense Analytics** | `/expenses/analytics/` | Vehicle Owner | Chart.js 12-month trends, category doughnut, vehicle comparisons |
| **Export Expense CSV** | `/expenses/export/` | Vehicle Owner | Download filtered expense transactions in CSV |
| **Nearby Fuel & EV Stations**| `/locations/` | Vehicle Owner | Leaflet.js map with distance badges and OSM directions |
| **Find Mechanics** | `/mechanics/find/` | Vehicle Owner | Browse accredited mechanics |
| **Mechanic Dashboard** | `/mechanics/dashboard/` | Mechanic | Incoming work orders, active repairs, billing |
| **Workshop Dashboard** | `/workshops/` | Workshop | Facility overview, estimates, bay management, billing |
| **Supplier Dashboard** | `/supplier/` | Supplier | Catalog management, stock shortages, order fulfillment |
| **Admin Dashboard** | `/admin-dashboard/` | Admin (Staff/Super) | Platform governance, accreditation, dispute resolution, audit logs |

---

## 13. Running Automated Tests

AutoVia includes a suite of **104 automated tests** covering authentication, RBAC, vehicles, expenses, locations, provider portals, admin governance, and end-to-end integration workflows.

### Run All 104 Tests:
```bash
python manage.py test
```

### Run Module-Specific Test Suites:
```bash
# Expense tracker, analytics, and CSV export tests (10 tests)
python manage.py test expenses.tests

# Fuel and EV charging station map & API tests (10 tests)
python manage.py test locations.tests

# End-to-end multi-module integration tests (5 workflows)
python manage.py test accounts.tests_integration

# Admin dashboard governance tests (14 tests)
python manage.py test accounts.tests_admin

# Authentication & RBAC tests (10 tests)
python manage.py test accounts.tests
```

### Verify System Integrity:
```bash
python manage.py check
```

---

## 14. Configuration & Security Notes

- **Object Ownership Isolation**: Users cannot view, modify, or delete vehicles, expenses, orders, or service requests belonging to other accounts.
- **Provider Verification Gating**: Unapproved or pending mechanics and workshops are filtered out of customer booking dropdowns until accredited by an administrator.
- **Atomic Concurrency Protection**: High-value transactions (such as order inventory deduction and request acceptance) utilize `transaction.atomic()` with `select_for_update()` row-level locks.
- **Admin Security**: `@admin_required` strictly enforces `request.user.is_staff or request.user.is_superuser`, returning **HTTP 403 Forbidden** for non-staff accounts regardless of profile metadata. Anti-lockout protection prevents administrators from deactivating their own accounts.
- **CSRF Protection**: All state-modifying requests require HTTP POST with Django CSRF tokens.
- **Map & Location Privacy**: GPS geolocation is strictly client-initiated with an explicit usage disclaimer. No private location data is stored on backend servers.

---

## 15. Known Limitations

- **External OSM / Overpass API Rate Limits**: Under heavy external load or network interruptions, public Overpass API calls may time out. AutoVia mitigates this using a 15-minute coordinate grid cache and dynamic proximity-based fallback stations.
- **Default Database**: The repository is configured with SQLite for zero-configuration local development. For production enterprise deployments with high concurrent read/write volumes, PostgreSQL is recommended.
>>>>>>> 6848f4c (k)

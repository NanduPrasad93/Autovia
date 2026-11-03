# AutoVia – Integrated Automobile Management and Assistance System

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

```bash
pip install -r requirements.txt
```

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

```bash
python manage.py createsuperuser
```

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

"""
db_setup.py
Builds the Voyager-style mock database (schema + synthetic data)
if it doesn't already exist. Called automatically by app.py so the
project is self-contained when deployed from GitHub.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta
from faker import Faker

DB_PATH = "voyager_mock.db"


def build_database():
    if os.path.exists(DB_PATH):
        return  # already built — nothing to do

    fake = Faker()
    random.seed(42)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ---------- SCHEMA ----------
    schema_sql = """
    CREATE TABLE IF NOT EXISTS properties (
        property_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        property_name   TEXT NOT NULL,
        address         TEXT NOT NULL,
        city            TEXT NOT NULL,
        state           TEXT NOT NULL,
        zip_code        TEXT NOT NULL,
        property_type   TEXT NOT NULL CHECK (property_type IN ('Residential', 'Commercial', 'Mixed-Use')),
        year_built      INTEGER,
        total_units     INTEGER
    );

    CREATE TABLE IF NOT EXISTS units (
        unit_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id     INTEGER NOT NULL,
        unit_number     TEXT NOT NULL,
        unit_type       TEXT CHECK (unit_type IN ('Studio', '1BR', '2BR', '3BR', 'Office', 'Retail')),
        square_feet     INTEGER,
        bedrooms        INTEGER,
        bathrooms       REAL,
        market_rent     DECIMAL(10, 2) NOT NULL,
        status          TEXT CHECK (status IN ('Occupied', 'Vacant', 'Down')) DEFAULT 'Vacant',
        FOREIGN KEY (property_id) REFERENCES properties(property_id)
    );

    CREATE TABLE IF NOT EXISTS tenants (
        tenant_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name      TEXT NOT NULL,
        last_name       TEXT NOT NULL,
        email           TEXT,
        phone           TEXT,
        move_in_date    DATE
    );

    CREATE TABLE IF NOT EXISTS leases (
        lease_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id         INTEGER NOT NULL,
        tenant_id       INTEGER NOT NULL,
        lease_start     DATE NOT NULL,
        lease_end       DATE NOT NULL,
        monthly_rent    DECIMAL(10, 2) NOT NULL,
        security_deposit DECIMAL(10, 2),
        lease_status    TEXT CHECK (lease_status IN ('Active', 'Expired', 'Pending', 'Terminated')) DEFAULT 'Active',
        FOREIGN KEY (unit_id) REFERENCES units(unit_id),
        FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
    );

    CREATE TABLE IF NOT EXISTS gl_transactions (
        transaction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id      INTEGER NOT NULL,
        lease_id         INTEGER,
        account_code     TEXT NOT NULL,
        account_category TEXT CHECK (account_category IN ('Income', 'Expense')),
        description      TEXT,
        amount           DECIMAL(10, 2) NOT NULL,
        transaction_date DATE NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(property_id),
        FOREIGN KEY (lease_id) REFERENCES leases(lease_id)
    );
    """
    cursor.executescript(schema_sql)
    conn.commit()

    # ---------- 1. PROPERTIES ----------
    property_types = ['Residential', 'Commercial', 'Mixed-Use']
    properties = []
    for i in range(15):
        properties.append((
            fake.company() + " " + random.choice(["Apartments", "Towers", "Plaza", "Residences", "Commons"]),
            fake.street_address(), fake.city(), fake.state_abbr(), fake.zipcode(),
            random.choice(property_types), random.randint(1975, 2020), None
        ))
    cursor.executemany("""
        INSERT INTO properties (property_name, address, city, state, zip_code, property_type, year_built, total_units)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, properties)
    conn.commit()

    cursor.execute("SELECT property_id FROM properties")
    property_ids = [row[0] for row in cursor.fetchall()]

    # ---------- 2. UNITS ----------
    unit_types = ['Studio', '1BR', '2BR', '3BR', 'Office', 'Retail']
    units = []
    for pid in property_ids:
        for u in range(1, random.randint(8, 20) + 1):
            unit_type = random.choice(unit_types)
            bedrooms = {'Studio': 0, '1BR': 1, '2BR': 2, '3BR': 3}.get(unit_type, 0)
            units.append((
                pid, f"{u}{random.choice(['A', 'B', 'C', ''])}", unit_type,
                random.randint(450, 2000), bedrooms, random.choice([1, 1.5, 2]),
                round(random.uniform(900, 3500), 2),
                random.choices(['Occupied', 'Vacant', 'Down'], weights=[75, 20, 5])[0]
            ))
    cursor.executemany("""
        INSERT INTO units (property_id, unit_number, unit_type, square_feet, bedrooms, bathrooms, market_rent, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, units)
    conn.commit()

    cursor.execute("""
        UPDATE properties
        SET total_units = (SELECT COUNT(*) FROM units WHERE units.property_id = properties.property_id)
    """)
    conn.commit()

    cursor.execute("SELECT unit_id, status, market_rent FROM units")
    unit_rows = cursor.fetchall()

    # ---------- 3. TENANTS ----------
    tenants = []
    for _ in range(100):
        tenants.append((fake.first_name(), fake.last_name(), fake.email(), fake.phone_number(),
                         fake.date_between(start_date="-3y", end_date="today")))
    cursor.executemany("""
        INSERT INTO tenants (first_name, last_name, email, phone, move_in_date)
        VALUES (?, ?, ?, ?, ?)
    """, tenants)
    conn.commit()

    cursor.execute("SELECT tenant_id FROM tenants")
    tenant_ids = [row[0] for row in cursor.fetchall()]

    # ---------- 4. LEASES ----------
    occupied_units = [u for u in unit_rows if u[1] == 'Occupied']
    leases = []
    for unit_id, status, market_rent in occupied_units:
        tenant_id = random.choice(tenant_ids)
        start = fake.date_between(start_date="-2y", end_date="-30d")
        end = start + timedelta(days=random.choice([365, 365, 730]))
        monthly_rent = round(market_rent * random.uniform(0.9, 1.05), 2)
        lease_status = 'Active' if end > datetime.now().date() else 'Expired'
        leases.append((unit_id, tenant_id, start, end, monthly_rent, round(monthly_rent, 2), lease_status))
    cursor.executemany("""
        INSERT INTO leases (unit_id, tenant_id, lease_start, lease_end, monthly_rent, security_deposit, lease_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, leases)
    conn.commit()

    # ---------- 5. GL TRANSACTIONS ----------
    expense_codes = [('5000-REPAIRS', 'Repairs & Maintenance'), ('5100-UTILITIES', 'Utilities'),
                      ('5200-INSURANCE', 'Insurance'), ('5300-MGMT-FEE', 'Management Fee')]

    cursor.execute("""
        SELECT leases.lease_id, units.property_id, leases.monthly_rent
        FROM leases JOIN units ON leases.unit_id = units.unit_id
    """)
    lease_property_map = cursor.fetchall()

    gl_transactions = []
    for lease_id, property_id, monthly_rent in lease_property_map:
        for month_offset in range(6):
            txn_date = datetime.now().date() - timedelta(days=30 * month_offset)
            gl_transactions.append((property_id, lease_id, '4000-RENT', 'Income',
                                     'Monthly rent charge', monthly_rent, txn_date))

    for pid in property_ids:
        for _ in range(random.randint(3, 8)):
            code, desc = random.choice(expense_codes)
            txn_date = fake.date_between(start_date="-6mo", end_date="today")
            amount = round(random.uniform(100, 2500), 2)
            gl_transactions.append((pid, None, code, 'Expense', desc, amount, txn_date))

    cursor.executemany("""
        INSERT INTO gl_transactions (property_id, lease_id, account_code, account_category, description, amount, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, gl_transactions)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    build_database()
    print("Database built successfully.")

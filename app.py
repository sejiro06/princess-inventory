from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "princess_inventory_secret_key_2026"

BASE_DIR = os.path.abspath(os.path.dirname(_file_))
DB_PATH = os.path.join(BASE_DIR, 'princess_inventory.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT,
                    price REAL,
                    stock INTEGER DEFAULT 0,
                    last_updated TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    product_name TEXT,
                    quantity INTEGER,
                    total_amount REAL,
                    sale_date TEXT,
                    customer_name TEXT,
                    is_credit INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS debts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    amount REAL,
                    remaining REAL,
                    date TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as total FROM products")
    total_products = c.fetchone()['total']
    
    c.execute("SELECT COUNT(*) as low FROM products WHERE stock < 10")
    low_stock = c.fetchone()['low']
    
    today = date.today().isoformat()
    c.execute("SELECT SUM(total_amount) as today_sales FROM sales WHERE sale_date = ?", (today,))
    today_sales = c.fetchone()['today_sales'] or 0
    
    c.execute("SELECT SUM(remaining) as total_debt FROM debts WHERE remaining > 0")
    total_debt = c.fetchone()['total_debt'] or 0
    
    conn.close()
    
    return render_template('dashboard.html', 
                           total_products=total_products, 
                           low_stock=low_stock,
                           today_sales=round(today_sales, 2),
                           total_debt=round(total_debt, 2))

# Add more routes later...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

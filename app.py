from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "princess_inventory_secret_key_2026"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
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
    selected_date = request.args.get('date', date.today().isoformat())
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as total FROM products")
    total_products = c.fetchone()['total']
    
    c.execute("SELECT COUNT(*) as low FROM products WHERE stock < 10")
    low_stock = c.fetchone()['low']
    
    c.execute("SELECT SUM(total_amount) as day_sales FROM sales WHERE sale_date = ?", (selected_date,))
    day_sales = c.fetchone()['day_sales'] or 0
    
    c.execute("SELECT SUM(remaining) as total_debt FROM debts WHERE remaining > 0")
    total_debt = c.fetchone()['total_debt'] or 0
    
    c.execute("SELECT * FROM sales WHERE sale_date = ? ORDER BY id DESC", (selected_date,))
    transactions = c.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                           total_products=total_products, 
                           low_stock=low_stock,
                           day_sales=round(day_sales, 2),
                           total_debt=round(total_debt, 2),
                           selected_date=selected_date,
                           transactions=transactions)

@app.route('/products')
def products():
    search = request.args.get('search', '')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if search:
        c.execute("SELECT * FROM products WHERE name LIKE ? ORDER BY name", (f'%{search}%',))
    else:
        c.execute("SELECT * FROM products ORDER BY name")
    products_list = c.fetchall()
    conn.close()
    return render_template('products.html', products=products_list, search=search)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO products (name, category, price, stock, last_updated) VALUES (?, ?, ?, ?, ?)",
                  (name, category, price, stock, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('add_product.html')

@app.route('/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    action = request.form['action']
    quantity = int(request.form['quantity'])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if action == 'add':
        c.execute("UPDATE products SET stock = stock + ?, last_updated = ? WHERE id = ?", 
                  (quantity, datetime.now().strftime("%Y-%m-%d %H:%M"), product_id))
    else:
        c.execute("UPDATE products SET stock = stock - ?, last_updated = ? WHERE id = ?", 
                  (quantity, datetime.now().strftime("%Y-%m-%d %H:%M"), product_id))
    conn.commit()
    conn.close()
    flash('Stock updated!', 'success')
    return redirect(url_for('products'))

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE stock > 0 ORDER BY name")
    products = c.fetchall()
    
    if request.method == 'POST':
        product_id = int(request.form['product_id'])
        quantity = int(request.form['quantity'])
        customer_name = request.form.get('customer_name', '').strip()
        sale_date = request.form.get('sale_date', date.today().isoformat())
        
        c.execute("SELECT name, price, stock FROM products WHERE id = ?", (product_id,))
        product = c.fetchone()
        
        if product and product['stock'] >= quantity:
            total_amount = product['price'] * quantity
            is_credit = 1 if customer_name else 0
            
            c.execute("""INSERT INTO sales 
                        (product_id, product_name, quantity, total_amount, sale_date, customer_name, is_credit) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (product_id, product['name'], quantity, total_amount, sale_date, customer_name, is_credit))
            
            c.execute("UPDATE products SET stock = stock - ?, last_updated = ? WHERE id = ?",
                      (quantity, datetime.now().strftime("%Y-%m-%d %H:%M"), product_id))
            
            if customer_name:
                c.execute("INSERT INTO debts (customer_name, amount, remaining, date) VALUES (?, ?, ?, ?)",
                          (customer_name, total_amount, total_amount, sale_date))
            
            conn.commit()
            flash('Transaction recorded successfully!', 'success')
        else:
            flash('Not enough stock!', 'danger')
        return redirect(url_for('sales'))
    
    filter_date = request.args.get('filter_date')
    if filter_date:
        c.execute("SELECT * FROM sales WHERE sale_date = ? ORDER BY id DESC", (filter_date,))
    else:
        c.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 50")
    sales_list = c.fetchall()
    conn.close()
    return render_template('sales.html', products=products, sales=sales_list, filter_date=filter_date)

@app.route('/debts')
def debts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT customer_name, SUM(remaining) as total_remaining, MAX(date) as last_date 
                 FROM debts GROUP BY customer_name HAVING total_remaining > 0 ORDER BY total_remaining DESC""")
    debt_list = c.fetchall()
    conn.close()
    return render_template('debts.html', debts=debt_list)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

from flask import Flask, render_template_string, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Main Admin Security PIN
ADMIN_PIN = "1234"

# SQLite Database Initialization
def init_db():
    conn = sqlite3.connect('repairs.db')
    cursor = conn.cursor()
    # Repair Jobs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            branch_name TEXT,
            customer_name TEXT,
            phone TEXT,
            device TEXT,
            issue TEXT,
            testing_cost INTEGER,
            repair_cost INTEGER,
            status TEXT
        )
    ''')
    # Dynamic Branches Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_name TEXT UNIQUE
        )
    ''')
    
    # Default initial main branch if database is empty
    cursor.execute('SELECT COUNT(*) FROM branches')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO branches (branch_name) VALUES (?)', ("Chinchwad Branch",))
        cursor.execute('INSERT INTO branches (branch_name) VALUES (?)', ("Ravet branch",))
        
    conn.commit()
    conn.close()

init_db()

STATUS_STAGES = [
    "1. Device Received (In Shop)",
    "2. Technician Assigned (Checking In-Progress)",
    "3. Under Review (Cost & Issues Estimated)",
    "4. Approved & Repairing",
    "5. Ready for Delivery",
    "6. Cancelled (Testing Charges Applicable)"
]

BASE_URL = "http://127.0.0.1:5000"

MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ARM TECH SERVICES</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; }
        h2, h3 { color: #1a252f; margin-bottom: 5px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 25px; }
        input, select, button { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { background-color: #007bff; color: white; border: none; font-weight: bold; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        th, td { border: 1px solid #dee2e6; padding: 10px; text-align: left; font-size: 13px; }
        th { background-color: #2c3e50; color: white; }
        
        .badge { padding: 5px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; display: inline-block; }
        .btn-update { background-color: #28a745; margin-top: 4px; padding: 6px; font-size: 12px; }
        .btn-whatsapp { background-color: #25D366; color: white; padding: 6px 10px; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 12px; display: inline-block; }
        .btn-whatsapp:hover { background-color: #128C7E; }
        .btn-delete { background-color: #dc3545; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; margin-top: 2px; }
        .btn-delete:hover { background-color: #bd2130; }
        .cost-box { width: 100px; padding: 4px; font-size: 12px; }
        .main-header { background: #1a252f; color: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .branch-badge { background: #e0a800; color: #000; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .add-branch-card { background: #fff3cd; border-left: 5px solid #ffc107; }
        .branch-list-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #eee; font-size: 13px; }
        .lock-badge { background: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .admin-badge { background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="main-header">
        <div>
            <h2 style="color: white; margin: 0;">💻 ARM TECH SERVICES</h2>
            <p style="margin: 5px 0 0 0; font-size: 13px; color: #17a2b8;">
                Current View: <b>{{ selected_branch }}</b>
            </p>
        </div>
        <div>
            {% if is_admin %}
                <span class="admin-badge">🔒 MAIN ADMIN ACCESS</span>
            {% else %}
                <span class="lock-badge">🔒 LOCKED BRANCH VIEW</span>
            {% endif %}
        </div>
    </div>

    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
        
        <!-- Filter Branch View Card (ONLY FOR MAIN ADMIN) -->
        {% if is_admin %}
        <div class="card" style="flex: 1; min-width: 260px; background: #e3f2fd;">
            <h3>🏪 Select Branch View</h3>
            <p style="font-size: 12px; color: #555;">पाहण्यासाठी शाखा निवडा:</p>
            <form action="/" method="GET">
                <input type="hidden" name="pin" value="{{ pin }}">
                <select name="branch" onchange="this.form.submit()">
                    <option value="All Branches (Main Admin View)" {% if selected_branch == "All Branches (Main Admin View)" %}selected{% endif %}>All Branches (Main Admin View)</option>
                    {% for b in branches %}
                        <option value="{{ b[1] }}" {% if b[1] == selected_branch %}selected{% endif %}>{{ b[1] }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>

        <!-- Dynamic Add & Manage Branch Card (ONLY FOR MAIN ADMIN) -->
        <div class="card add-branch-card" style="flex: 1.2; min-width: 300px;">
            <h3>➕ Manage Branches / Locations</h3>
            <form action="/add_branch" method="POST">
                <input type="hidden" name="pin" value="{{ pin }}">
                <input type="text" name="new_branch_name" placeholder="उदा. Baner Branch" required>
                <button type="submit" style="background-color: #ffc107; color: black; font-size: 13px;">Add New Branch</button>
            </form>

            <h4 style="margin: 15px 0 5px 0; font-size: 13px;">उपलब्ध शाखा (Delete करण्यासाठी):</h4>
            <div style="max-height: 120px; overflow-y: auto;">
                {% for b in branches %}
                    <div class="branch-list-item">
                        <span>• {{ b[1] }}</span>
                        <form action="/delete_branch/{{ b[0] }}" method="POST" style="margin: 0; width: auto;" onsubmit="return confirm('ही शाखा काढून टाकायची आहे का?');">
                            <input type="hidden" name="pin" value="{{ pin }}">
                            <button type="submit" class="btn-delete">Delete</button>
                        </form>
                    </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Add Job Card (For Both Admin and Branch Staff) -->
        <div class="card" style="flex: 1.8; min-width: 320px;">
            <h3>📝 New Job Card Entry</h3>
            <form action="/add" method="POST">
                <input type="hidden" name="pin" value="{{ pin }}">
                <label style="font-size: 12px; font-weight: bold;">शाखा (Select Shop Branch):</label>
                
                {% if is_admin %}
                    <select name="branch_name" required>
                        {% for b in branches %}
                            <option value="{{ b[1] }}">{{ b[1] }}</option>
                        {% endfor %}
                    </select>
                {% else %}
                    <input type="text" name="branch_name" value="{{ selected_branch }}" readonly style="background-color: #e9ecef; font-weight: bold;">
                {% endif %}

                <input type="text" name="name" placeholder="Customer Name" required>
                <input type="text" name="phone" placeholder="Phone Number (e.g. 9876543210)" required>
                <input type="text" name="device" placeholder="Device Model (e.g. Dell / HP)" required>
                <input type="text" name="issue" placeholder="Problem / Issue Reported" required>
                <input type="number" name="testing_cost" placeholder="Fixed Testing Charges (Rs.)" value="300" required>
                <button type="submit">Create Job Card</button>
            </form>
        </div>
    </div>

    <h3>📋 Repair Jobs Log ({{ selected_branch }})</h3>
    <table>
        <thead>
            <tr>
                <th>Job ID</th>
                <th>Branch</th>
                <th>Date & Time</th>
                <th>Customer</th>
                <th>Phone</th>
                <th>Device</th>
                <th>Testing Fee</th>
                <th>Repair Cost</th>
                <th>Current Status</th>
                <th>WhatsApp Share</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {% for job in repairs %}
            <tr>
                <td><b>#{{ job[0] }}</b></td>
                <td><span class="branch-badge">{{ job[2] }}</span></td>
                <td><small>{{ job[1] }}</small></td>
                <td><b>{{ job[3] }}</b></td>
                <td>{{ job[4] }}</td>
                <td>{{ job[5] }}</td>
                <td><b>₹{{ job[7] }}</b></td>
                <td><b style="color: #28a745; font-size: 14px;">₹{{ job[8] }}</b></td>
                <td><span class="badge">{{ job[9] }}</span></td>
                <td>
                    {% set tracking_url = base_url + "/track/" + (job[0]|string) %}
                    {% set wa_msg = "Hello " + job[3] + ", Track your " + job[5] + " repair status here: " + tracking_url %}
                    <a href="https://wa.me/91{{ job[4] }}?text={{ wa_msg | urlencode }}" target="_blank" class="btn-whatsapp">
                        📲 Send WhatsApp
                    </a>
                </td>
                <td>
                    <form action="/update_job/{{ job[0] }}" method="POST">
                        <input type="hidden" name="pin" value="{{ pin }}">
                        <input type="hidden" name="branch" value="{{ selected_branch }}">
                        <input type="number" name="repair_cost" value="{{ job[8] }}" class="cost-box" required>
                        <select name="next_status">
                            {% for stage in stages %}
                                <option value="{{ stage }}" {% if stage == job[9] %}selected{% endif %}>{{ stage }}</option>
                            {% endfor %}
                        </select>
                        <button type="submit" class="btn-update">Update</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
'''

CUSTOMER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARM Tech Services - Repair Status</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
        h2 { color: #007bff; margin-bottom: 5px; }
        .shop-sub { color: #6c757d; font-size: 14px; margin-bottom: 25px; }
        .info-group { text-align: left; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .label { font-size: 12px; color: #888; text-transform: uppercase; font-weight: bold; }
        .value { font-size: 16px; color: #333; margin-top: 3px; }
        .status-badge { display: inline-block; padding: 8px 15px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-top: 10px; background-color: #ffc107; color: #000; }
    </style>
</head>
<body>
    <div class="card">
        <h2>ARM Tech Services</h2>
        <div class="shop-sub">Repair Status Tracker</div>
        
        <div class="info-group">
            <div class="label">Customer Name</div>
            <div class="value">{{ job[2] }}</div>
        </div>
        
        <div class="info-group">
            <div class="label">Device Model</div>
            <div class="value">{{ job[4] }}</div>
        </div>

        <div class="info-group">
            <div class="label">Reported Issue</div>
            <div class="value">{{ job[5] }}</div>
        </div>

        <div class="info-group">
            <div class="label">Current Status</div>
            <div><span class="status-badge">{{ job[7] }}</span></div>
        </div>
    </div>
</body>
</html>
"""
@app.route('/')
def home():
    pin = request.args.get('pin', '')
    is_admin = (pin == ADMIN_PIN)
    
    selected_branch = request.args.get('branch', '')
    
    conn = sqlite3.connect('repairs.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM branches')
    branches = cursor.fetchall()
    
    if is_admin:
        if not selected_branch:
            selected_branch = 'All Branches (Main Admin View)'
        
        if selected_branch == 'All Branches (Main Admin View)':
            cursor.execute('SELECT * FROM repairs ORDER BY id DESC')
        else:
            cursor.execute('SELECT * FROM repairs WHERE branch_name = ? ORDER BY id DESC', (selected_branch,))
    else:
        # Restricted Branch Mode
        if not selected_branch or selected_branch == 'All Branches (Main Admin View)':
            selected_branch = branches[0][1] if branches else 'Chinchwad Branch'
            
        cursor.execute('SELECT * FROM repairs WHERE branch_name = ? ORDER BY id DESC', (selected_branch,))
        
    repairs = cursor.fetchall()
    conn.close()
    
    return render_template_string(MAIN_TEMPLATE, repairs=repairs, stages=STATUS_STAGES, branches=branches, selected_branch=selected_branch, base_url=BASE_URL, is_admin=is_admin, pin=pin)

@app.route('/add_branch', methods=['POST'])
def add_branch():
    pin = request.form.get('pin', '')
    if pin == ADMIN_PIN:
        new_branch = request.form['new_branch_name']
        if new_branch:
            conn = sqlite3.connect('repairs.db')
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO branches (branch_name) VALUES (?)', (new_branch,))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
            conn.close()
    return redirect(f'/?pin={pin}')

@app.route('/delete_branch/<int:branch_id>', methods=['POST'])
def delete_branch(branch_id):
    pin = request.form.get('pin', '')
    if pin == ADMIN_PIN:
        conn = sqlite3.connect('repairs.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM branches WHERE id = ?', (branch_id,))
        conn.commit()
        conn.close()
    return redirect(f'/?pin={pin}')

@app.route('/add', methods=['POST'])
def add():
    pin = request.form.get('pin', '')
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    conn = sqlite3.connect('repairs.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO repairs (created_at, branch_name, customer_name, phone, device, issue, testing_cost, repair_cost, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (now, request.form['branch_name'], request.form['name'], request.form['phone'], request.form['device'], request.form['issue'], request.form['testing_cost'], 0, STATUS_STAGES[0]))
    conn.commit()
    conn.close()
    return redirect(f'/?pin={pin}&branch={request.form["branch_name"]}')

@app.route('/update_job/<int:job_id>', methods=['POST'])
def update_job(job_id):
    pin = request.form.get('pin', '')
    branch = request.form.get('branch', '')
    conn = sqlite3.connect('repairs.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE repairs SET repair_cost = ?, status = ? WHERE id = ?
    ''', (request.form['repair_cost'], request.form['next_status'], job_id))
    conn.commit()
    conn.close()
    return redirect(f'/?pin={pin}&branch={branch}')

@app.route('/track/<int:job_id>')
def track_customer(job_id):
    conn = sqlite3.connect('repairs.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM repairs WHERE id = ?', (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if job:
        return render_template_string(CUSTOMER_TEMPLATE, job=job)
    return "<h3>Invalid Job ID / Record Not Found</h3>"

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

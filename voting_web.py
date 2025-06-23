from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import csv
import json
import os
import os
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    votes = db.Column(db.Integer, default=0)

class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    has_voted = db.Column(db.Boolean, default=False)

# Create tables
with app.app_context():
    db.create_all()

# Admin password
ADMIN_PASSWORD = "admin123"

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        # Handle admin login
        password = request.form.get('password')
        if password != ADMIN_PASSWORD:
            flash('Incorrect password. Access denied.', 'danger')
            return redirect(url_for('admin_panel'))
        
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_panel'))
    
    if request.method == 'POST':
        # Handle adding candidates
        candidate_names = request.form.get('candidates')
        if candidate_names:
            names = [name.strip() for name in candidate_names.split(',') if name.strip()]
            for name in names:
                if not Candidate.query.filter_by(name=name).first():
                    new_candidate = Candidate(name=name)
                    db.session.add(new_candidate)
            db.session.commit()
            flash('Candidates added successfully!', 'success')
    
    candidates = Candidate.query.all()
    return render_template('admin_dashboard.html', candidates=candidates)

@app.route('/admin/reset', methods=['POST'])
def reset_system():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_panel'))
    
    # Clear all data
    db.session.query(Candidate).delete()
    db.session.query(Voter).delete()
    db.session.commit()
    flash('System has been reset successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/vote', methods=['GET', 'POST'])
def voter_panel():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        candidate_id = request.form.get('candidate_id')
        
        if not phone_number or not candidate_id:
            flash('Please provide both phone number and select a candidate', 'danger')
            return redirect(url_for('voter_panel'))
        
        # Check if voter already voted
        voter = Voter.query.filter_by(phone_number=phone_number).first()
        if voter and voter.has_voted:
            flash('This phone number has already voted.', 'danger')
            return redirect(url_for('voter_panel'))
        
        # Register voter or update status
        if not voter:
            voter = Voter(phone_number=phone_number, has_voted=True)
            db.session.add(voter)
        else:
            voter.has_voted = True
        
        # Update candidate votes
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            candidate.votes += 1
            db.session.commit()
            flash('Vote cast successfully!', 'success')
        else:
            flash('Invalid candidate selected', 'danger')
        
        return redirect(url_for('voter_panel'))
    
    candidates = Candidate.query.all()
    return render_template('voter_panel.html', candidates=candidates)

@app.route('/results')
def results_panel():
    candidates = Candidate.query.order_by(Candidate.votes.desc()).all()
    
    # Create chart
    img = BytesIO()
    if candidates:
        names = [c.name for c in candidates]
        votes = [c.votes for c in candidates]
        
        plt.figure(figsize=(8, 5))
        plt.pie(votes, labels=names, autopct='%1.1f%%', startangle=140, colors=plt.cm.tab20.colors)
        plt.title("Live Voting Results")
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)
        chart_url = base64.b64encode(img.getvalue()).decode('utf8')
    else:
        chart_url = None
    
    return render_template('results.html', candidates=candidates, chart_url=chart_url)

@app.route('/export/csv')
def export_csv():
    candidates = Candidate.query.all()
    
    # Create CSV in memory
    csv_data = BytesIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Candidate', 'Votes'])
    for candidate in candidates:
        writer.writerow([candidate.name, candidate.votes])
    
    csv_data.seek(0)
    return send_file(
        csv_data,
        mimetype='text/csv',
        as_attachment=True,
        download_name='voting_results.csv'
    )

@app.route('/export/json')
def export_json():
    candidates = Candidate.query.all()
    results = {candidate.name: candidate.votes for candidate in candidates}
    
    # Create JSON in memory
    json_data = BytesIO()
    json_data.write(json.dumps(results, indent=4).encode('utf-8'))
    json_data.seek(0)
    return send_file(
        json_data,
        mimetype='application/json',
        as_attachment=True,
        download_name='voting_results.json'
    )

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

if __name__ == '__main__':
    app.run(debug=True)

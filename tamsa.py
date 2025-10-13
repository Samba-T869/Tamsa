from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'thebaddhdshs'

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

def init_db():
	conn = sqlite3.connect('tamsa.db')
	cur = conn.cursor()
	cur.execute('''
	CREATE TABLE IF NOT EXISTS users(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	fullname TEXT UNIQUE NOT NULL,
	email TEXT UNIQUE NOT NULL, 
	password TEXT NOT NULL
	)
	''')
	cur.execute('''
    CREATE TABLE IF NOT EXISTS documents(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    filename TEXT NOT NULL,
    cloudinary_url TEXT NOT NULL,
    cloudinary_public_id TEXT NOT NULL,
    uploader TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
	cur.execute('''
CREATE TABLE IF NOT EXISTS activities(
id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT NOT NULL,
description TEXT NOT NULL,
date TEXT NOT NULL,
location TEXT NOT NULL,
media_url TEXT,
media_public_id TEXT,
media_type TEXT, -- 'image' or 'video'
author TEXT NOT NULL,
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
	cur.execute('''
    CREATE TABLE IF NOT EXISTS leaders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    picture_url TEXT NOT NULL,
    picture_public_id TEXT NOT NULL,
    bio TEXT,
    order_index INTEGER DEFAULT 0,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
	cur.execute('''
CREATE TABLE IF NOT EXISTS opportunities (
id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT NOT NULL,
description TEXT NOT NULL,
type TEXT NOT NULL, -- 'opportunity' or 'announcement'
deadline TEXT, -- For opportunities
event_date TEXT, -- For announcements/events
location TEXT,
author TEXT NOT NULL,
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
	conn.commit()
	conn.close()
	
init_db()

# Routes
@app.route('/')
def home():
	return render_template('homepage.html')
	
@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method =='POST':
		fullname = request.form['fullname']
		email = request.form['email']
		password = request.form['password']
		confpass = request. form['confpass']
		flash(f'Registered successfully please login')
		return redirect(url_for('login'))
	return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method =='POST':
    	email = request.form['email']
    	password = request.form['password']
    	return redirect(url_for('home'))
    return render_template('login.html')
    
@app.route('/documents', methods=['GET', 'POST'])
def documents():
    if request.method == 'POST':
        # Handle document upload
        title = request.form.get('title')
        category = request.form.get('category')
        file = request.files.get('file')
        
        if file and file.filename != '':
            # Check if file is PDF
            if file.content_type != 'application/pdf':
                flash('Please upload only PDF files', 'error')
                return redirect(request.url)
            
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    file,
                    resource_type = "raw",  # Use "raw" for PDF files
                    folder = "tamsa/documents",
                    use_filename = True
                )
                
                # Save document info to database
                conn = sqlite3.connect('tamsa.db')
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO documents (title, category, filename, cloudinary_url, cloudinary_public_id, uploader)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (title, category, file.filename, upload_result['secure_url'], upload_result['public_id'], 'User'))
                
                conn.commit()
                conn.close()
                
                flash('Document uploaded successfully!', 'success')
                
            except Exception as e:
                flash(f'Error uploading file: {str(e)}', 'error')
        
        return redirect(url_for('documents'))
    
    # GET request - fetch documents from database
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM documents ORDER BY upload_date DESC')
    documents_data = cur.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for easier template handling
    documents_list = []
    for doc in documents_data:
        documents_list.append({
            'id': doc[0],
            'title': doc[1],
            'category': doc[2],
            'filename': doc[3],
            'url': doc[4],
            'public_id': doc[5],
            'uploader': doc[6],
            'upload_date': doc[7]
        })
    
    return render_template('documents.html', documents=documents_list)

@app.route('/documents/delete/<int:doc_id>', methods=['POST'])
def delete_document(doc_id):
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT cloudinary_public_id FROM documents WHERE id = ?', (doc_id,))
    result = cur.fetchone()
    
    if result:
        public_id = result[0]
        try:
            # Delete from Cloudinary
            cloudinary.uploader.destroy(public_id, resource_type="raw")
            # Delete from database
            cur.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            conn.commit()
            flash('Document deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting document: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('documents'))

@app.route('/opportunities', methods=['GET', 'POST'])
def opportunities():
    if request.method == 'POST':
        # Handle opportunity/announcement creation
        title = request.form.get('title')
        description = request.form.get('description')
        type_ = request.form.get('type')  # 'opportunity' or 'announcement'
        deadline = request.form.get('deadline')
        event_date = request.form.get('event_date')
        location = request.form.get('location')
        
        # Validate required fields
        if not title or not description or not type_:
            flash('Please fill in all required fields', 'error')
            return redirect(request.url)
        
        # Validate type-specific fields
        if type_ == 'opportunity' and not deadline:
            flash('Please provide a deadline for opportunities', 'error')
            return redirect(request.url)
        
        if type_ == 'announcement' and not event_date:
            flash('Please provide an event date for announcements', 'error')
            return redirect(request.url)
        
        # Save to database
        conn = sqlite3.connect('tamsa.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO opportunities (title, description, type, deadline, event_date, location, author)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, type_, deadline, event_date, location, 'User'))
        
        conn.commit()
        conn.close()
        
        flash('Posted successfully!', 'success')
        return redirect(url_for('opportunities'))
    
    # GET request - fetch opportunities and announcements from database
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM opportunities ORDER BY created_date DESC')
    opportunities_data = cur.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for easier template handling
    opportunities_list = []
    for opp in opportunities_data:
        opportunities_list.append({
            'id': opp[0],
            'title': opp[1],
            'description': opp[2],
            'type': opp[3],
            'deadline': opp[4],
            'event_date': opp[5],
            'location': opp[6],
            'author': opp[7],
            'created_date': opp[8]
        })
    
    return render_template('opportunities.html', opportunities=opportunities_list)

@app.route('/opportunities/delete/<int:opp_id>', methods=['POST'])
def delete_opportunity(opp_id):
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM opportunities WHERE id = ?', (opp_id,))
    conn.commit()
    conn.close()
    
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('opportunities'))

@app.route('/opportunities/add', methods=['GET'])
def add_opportunity_form():
    return render_template('add_opportunity.html')
    
@app.route('/activities', methods=['GET', 'POST'])
def activities():
    if request.method == 'POST':
        # Handle activity creation with media upload
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        location = request.form.get('location')
        file = request.files.get('media_file')
        
        media_url = None
        media_public_id = None
        media_type = None
        
        if file and file.filename != '':
            # Check if file is image or video
            allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            allowed_video_types = ['video/mp4', 'video/mov', 'video/avi', 'video/webm']
            
            if file.content_type in allowed_image_types:
                media_type = 'image'
                resource_type = 'image'
            elif file.content_type in allowed_video_types:
                media_type = 'video'
                resource_type = 'video'
            else:
                flash('Please upload only image or video files', 'error')
                return redirect(request.url)
            
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    file,
                    resource_type=resource_type,
                    folder="tamsa/activities",
                    use_filename=True
                )
                
                media_url = upload_result['secure_url']
                media_public_id = upload_result['public_id']
                
            except Exception as e:
                flash(f'Error uploading media: {str(e)}', 'error')
                return redirect(request.url)
        
        # Save activity to database
        conn = sqlite3.connect('tamsa.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO activities (title, description, date, location, media_url, media_public_id, media_type, author)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, date, location, media_url, media_public_id, media_type, 'User'))
        
        conn.commit()
        conn.close()
        
        flash('Activity posted successfully!', 'success')
        return redirect(url_for('activities'))
    
    # GET request - fetch activities from database
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM activities ORDER BY created_date DESC')
    activities_data = cur.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for easier template handling
    activities_list = []
    for activity in activities_data:
        activities_list.append({
            'id': activity[0],
            'title': activity[1],
            'description': activity[2],
            'date': activity[3],
            'location': activity[4],
            'media_url': activity[5],
            'media_public_id': activity[6],
            'media_type': activity[7],
            'author': activity[8],
            'created_date': activity[9]
        })
    
    return render_template('activities.html', activities=activities_list)

@app.route('/activities/delete/<int:activity_id>', methods=['POST'])
def delete_activity(activity_id):
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT media_public_id, media_type FROM activities WHERE id = ?', (activity_id,))
    result = cur.fetchone()
    
    if result:
        public_id = result[0]
        media_type = result[1]
        if public_id:  # Only delete from Cloudinary if there's media
            try:
                # Delete from Cloudinary
                resource_type = 'image' if media_type == 'image' else 'video'
                cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            except Exception as e:
                flash(f'Error deleting media: {str(e)}', 'error')
        
        # Delete from database
        cur.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
        conn.commit()
        flash('Activity deleted successfully!', 'success')
    
    conn.close()
    return redirect(url_for('activities'))     

@app.route('/leadership', methods=['GET', 'POST'])
def leadership():
    if request.method == 'POST':
        # Handle leader creation
        name = request.form.get('name')
        position = request.form.get('position')
        bio = request.form.get('bio')
        order_index = request.form.get('order_index', 0)
        file = request.files.get('picture')
        
        if not file or file.filename == '':
            flash('Please select a picture', 'error')
            return redirect(request.url)
        
        # Check if file is an image
        allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed_image_types:
            flash('Please upload only image files (JPEG, PNG, GIF, WebP)', 'error')
            return redirect(request.url)
        
        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                resource_type='image',
                folder="tamsa/leaders",
                use_filename=True
            )
            
            # Save leader info to database
            conn = sqlite3.connect('tamsa.db')
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO leaders (name, position, picture_url, picture_public_id, bio, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, position, upload_result['secure_url'], upload_result['public_id'], bio, order_index))
            
            conn.commit()
            conn.close()
            
            flash('Leader added successfully!', 'success')
            
        except Exception as e:
            flash(f'Error uploading picture: {str(e)}', 'error')
        
        return redirect(url_for('leadership'))
    
    # GET request - fetch leaders from database
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM leaders ORDER BY order_index, created_date DESC')
    leaders_data = cur.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for easier template handling
    leaders_list = []
    for leader in leaders_data:
        leaders_list.append({
            'id': leader[0],
            'name': leader[1],
            'position': leader[2],
            'picture_url': leader[3],
            'picture_public_id': leader[4],
            'bio': leader[5],
            'order_index': leader[6],
            'created_date': leader[7]
        })
    
    return render_template('leadership.html', leaders=leaders_list)

@app.route('/leadership/delete/<int:leader_id>', methods=['POST'])
def delete_leader(leader_id):
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    cur.execute('SELECT picture_public_id FROM leaders WHERE id = ?', (leader_id,))
    result = cur.fetchone()
    
    if result:
        public_id = result[0]
        try:
            # Delete from Cloudinary
            cloudinary.uploader.destroy(public_id, resource_type="image")
            # Delete from database
            cur.execute('DELETE FROM leaders WHERE id = ?', (leader_id,))
            conn.commit()
            flash('Leader deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting leader: {str(e)}', 'error')
    
    conn.close()
    return redirect(url_for('leadership'))
    
@app.route('/leadership/add', methods=['GET'])
def add_leader_form():
    return render_template('add_leader.html')
    
if __name__ == '__main__':
    app.run(port='8000', debug=True)
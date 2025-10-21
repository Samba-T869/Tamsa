from flask import Blueprint, redirect, url_for, render_template, session, request, flash, jsonify
import sqlite3
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import time
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

actions_bp = Blueprint('actions_bp', __name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

@actions_bp.route('/actions', methods=['GET', 'POST'])
def actions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Fetch all posts from all categories
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    
    # Fetch leaders
    cur.execute('SELECT id, name, "leadership" as type, created_date FROM leaders ORDER BY created_date DESC')
    leaders = cur.fetchall()
    
    # Fetch opportunities (announcements and opportunities)
    cur.execute('SELECT id, title, type, created_date FROM opportunities ORDER BY created_date DESC')
    opportunities = cur.fetchall()
    
    # Fetch activities
    cur.execute('SELECT id, title, "activity" as type, created_date FROM activities ORDER BY created_date DESC')
    activities = cur.fetchall()
    
    # Fetch documents
    cur.execute('SELECT id, title, "document" as type, upload_date FROM documents ORDER BY upload_date DESC')
    documents = cur.fetchall()
    
    conn.close()
    
    # Combine all posts
    all_posts = []
    
    # Add leaders
    for post in leaders:
        all_posts.append({
            'id': post[0],
            'title': post[1],
            'type': post[2],
            'date': post[3],
            'category': 'Leadership'
        })
    
    # Add opportunities and announcements
    for post in opportunities:
        category = 'Announcement' if post[2] == 'announcement' else 'Opportunity'
        all_posts.append({
            'id': post[0],
            'title': post[1],
            'type': post[2],
           'date': post[3],
            'category': category
        })
    
    for post in activities:
        all_posts.append({
        'id': post[0],
        'title': post[1],
        'type': post[2],
        'date': post[3],
        'category': 'Activity'
    })
    
    for post in documents:
        all_posts.append({
        'id': post[0],
        'title': post[1],
        'type': post[2],
        'date': post[3],
        'category': 'Document'
    })
    
    # Sort by date (newest first)
    all_posts.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('actions.html', posts=all_posts)

@actions_bp.route('/actions/delete/<string:category>/<int:post_id>', methods=['POST'])
def delete_post(category, post_id):
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('tamsa.db')
    cur = conn.cursor()
    
    try:
        if category == 'Leadership':
            # Get public_id for Cloudinary deletion
            cur.execute('SELECT picture_public_id FROM leaders WHERE id = ?', (post_id,))
            result = cur.fetchone()
            if result and result[0]:
                cloudinary.uploader.destroy(result[0], resource_type="image")
            
            cur.execute('DELETE FROM leaders WHERE id = ?', (post_id,))
        
        elif category == 'Opportunity' or category == 'Announcement':
            # Get public_id for Cloudinary deletion
            cur.execute('SELECT media_public_id, media_type FROM opportunities WHERE id = ?', (post_id,))
            result = cur.fetchone()
            if result and result[0]:
                resource_type = 'image' if result[1] == 'image' else 'video'
                cloudinary.uploader.destroy(result[0], resource_type=resource_type)
            
            cur.execute('DELETE FROM opportunities WHERE id = ?', (post_id,))
        
        elif category == 'Activity':
            # Get public_id for Cloudinary deletion
            cur.execute('SELECT media_public_id, media_type FROM activities WHERE id = ?', (post_id,))
            result = cur.fetchone()
            if result and result[0]:
                resource_type = 'image' if result[1] == 'image' else 'video'
                cloudinary.uploader.destroy(result[0], resource_type=resource_type)
            
            cur.execute('DELETE FROM activities WHERE id = ?', (post_id,))
        
        elif category == 'Document':
            # Get public_id for Cloudinary deletion
            cur.execute('SELECT cloudinary_public_id FROM documents WHERE id = ?', (post_id,))
            result = cur.fetchone()
            if result and result[0]:
                cloudinary.uploader.destroy(result[0], resource_type="raw")
            
            cur.execute('DELETE FROM documents WHERE id = ?', (post_id,))
        
        conn.commit()
        flash(f'{category} post deleted successfully!', 'success')
        return jsonify({'success': True, 'message': 'Post deleted successfully'})
    
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting post: {str(e)}', 'error')
        return jsonify({'success': False, 'message': str(e)}), 500
    
    finally:
        conn.close()
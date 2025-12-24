from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, User, Photo, Vote, Comment, Notification
from forms import RegistrationForm, LoginForm, PhotoUploadForm, CommentForm, ProfileUpdateForm
from utils import save_photo, create_notification, allowed_file
from auth import admin_required, voter_required, participant_required, load_user
from datetime import datetime
from flask_wtf.csrf import CSRFProtect, generate_csrf
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)

# Ensure all required directories exist
basedir = os.path.abspath(os.path.dirname(__file__))
with app.app_context():
    # Create upload directories if they don't exist
    upload_folders = [
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pictures'),
        os.path.join(basedir, 'static', 'uploads', 'profile_pictures'),
        'static/uploads/profile_pictures'
    ]
    
    for folder in upload_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created directory: {folder}")

# Create database tables and default admin
with app.app_context():
    db.create_all()
    # Create default admin user if not exists
    if not User.query.filter_by(email='admin@snapshowdown.com').first():
        admin = User(
            email='admin@snapshowdown.com',
            username='Admin',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create default participant and voter for testing
        participant = User(
            email='participant@example.com',
            username='Participant',
            role='participant'
        )
        participant.set_password('password123')
        db.session.add(participant)
        
        voter = User(
            email='voter@example.com',
            username='Voter',
            role='voter'
        )
        voter.set_password('password123')
        db.session.add(voter)
        
        db.session.commit()
        print("Default users created:")
        print("- Admin: admin@snapshowdown.com / admin123")
        print("- Participant: participant@example.com / password123")
        print("- Voter: voter@example.com / password123")

# ============ MAIN ROUTES ============

@app.route('/')
def home():
    approved_photos = Photo.query.filter_by(status='approved').order_by(Photo.votes_count.desc()).limit(8).all()
    return render_template('home.html', photos=approved_photos)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/leaderboard')
def leaderboard():
    top_photos = Photo.query.filter_by(status='approved')\
                           .order_by(Photo.votes_count.desc())\
                           .limit(20)\
                           .all()
    return render_template('leaderboard.html', 
                         top_photos=top_photos,
                         current_time=datetime.utcnow())

@app.route('/previous-winners')
def previous_winners():
    winners = Photo.query.filter_by(status='approved')\
                        .order_by(Photo.votes_count.desc())\
                        .limit(3)\
                        .all()
    return render_template('previous_winners.html', winners=winners)

@app.route('/gallery')
def gallery():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    photos = Photo.query.filter_by(status='approved')\
                       .order_by(Photo.votes_count.desc())\
                       .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('gallery.html', photos=photos)

@app.route('/photo/<int:photo_id>')
def photo_detail(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if photo is approved (unless user is admin or owner)
    if photo.status != 'approved' and not current_user.is_authenticated:
        flash('This photo is not available for viewing.', 'error')
        return redirect(url_for('gallery'))
    
    if photo.status != 'approved' and current_user.is_authenticated:
        if not (current_user.is_admin() or current_user.id == photo.user_id):
            flash('This photo is not available for viewing.', 'error')
            return redirect(url_for('gallery'))
    
    return render_template('photo_detail.html', photo=photo)

# ============ AUTHENTICATION ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Force role to be either participant or voter only
        role = form.role.data
        if role == 'admin':  # Prevent admin registration through form
            role = 'participant'
            
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=role
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# ============ USER PROFILE ROUTES ============

@app.route('/profile')
@login_required
def profile():
    user_photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.upload_date.desc()).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    
    # Calculate counts for the template
    approved_count = sum(1 for photo in user_photos if photo.status == 'approved')
    pending_count = sum(1 for photo in user_photos if photo.status == 'pending')
    
    return render_template('profile.html', 
                         photos=user_photos, 
                         notifications=notifications,
                         approved_count=approved_count,
                         pending_count=pending_count,
                         photos_count=len(user_photos))

@app.route('/upload-profile-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Save the file
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Generate unique filename
        new_filename = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Ensure profile pictures directory exists
        profile_pic_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pictures')
        os.makedirs(profile_pic_dir, exist_ok=True)
        
        filepath = os.path.join(profile_pic_dir, new_filename)
        file.save(filepath)
        
        # Update user profile
        current_user.profile_picture = new_filename
        db.session.commit()
        
        return jsonify({'success': True, 'filename': new_filename})
    
    return jsonify({'error': 'Invalid file type. Only JPG, PNG, GIF allowed.'}), 400

@app.route('/upload', methods=['GET', 'POST'])
@login_required
@participant_required
def upload_photo():
    form = PhotoUploadForm()
    
    if form.validate_on_submit():
        try:
            # Check if file exists
            if not form.photo.data:
                flash('Please select a photo to upload.', 'error')
                return render_template('upload.html', form=form)
            
            # Save the photo
            filename = save_photo(form.photo.data)
            if not filename:
                flash('Invalid file type. Please upload JPG, PNG, or GIF.', 'error')
                return render_template('upload.html', form=form)
            
            # Create photo record
            photo = Photo(
                title=form.title.data,
                description=form.description.data,
                filename=filename,
                user_id=current_user.id,
                status='pending'
            )
            
            db.session.add(photo)
            db.session.commit()
            
            # Create notification
            create_notification(current_user.id, f'Your photo "{photo.title}" has been submitted for review.')
            
            flash('Photo submitted successfully! It will be reviewed by admin.', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error uploading photo: {e}")
            flash(f'Error uploading photo: {str(e)}', 'error')
            return render_template('upload.html', form=form)
    
    # For debugging: check form errors
    if request.method == 'POST':
        print(f"Form errors: {form.errors}")
        flash('Please check the form for errors.', 'error')
    
    return render_template('upload.html', form=form)

# ============ VOTING & COMMENTING ROUTES ============

@app.route('/vote')
@login_required
def vote_page():
    approved_photos = Photo.query.filter_by(status='approved').all()
    return render_template('vote.html', photos=approved_photos)

@app.route('/vote/<int:photo_id>', methods=['POST'])
@login_required
def vote(photo_id):
    try:
        # Debug logging
        print(f"\n=== VOTE ATTEMPT ===")
        print(f"User ID: {current_user.id}")
        print(f"Username: {current_user.username}")
        print(f"User Role: {current_user.role}")
        print(f"Photo ID: {photo_id}")
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            print("User not authenticated")
            return jsonify({'success': False, 'error': 'Please login to vote.'}), 401
        
        # Check if user can vote
        if not current_user.is_voter():
            print(f"User cannot vote. Role: {current_user.role}, is_voter(): {current_user.is_voter()}")
            return jsonify({'success': False, 'error': 'You do not have permission to vote.'}), 403
        
        photo = Photo.query.get_or_404(photo_id)
        print(f"Photo found: {photo.title}, Status: {photo.status}, Owner: {photo.user_id}")
        
        # Check if photo is approved
        if photo.status != 'approved':
            print(f"Photo not approved. Status: {photo.status}")
            return jsonify({'success': False, 'error': 'You can only vote for approved photos.'}), 400
        
        # Check if user already voted
        existing_vote = Vote.query.filter_by(user_id=current_user.id, photo_id=photo_id).first()
        if existing_vote:
            print(f"User already voted at: {existing_vote.voted_at}")
            return jsonify({'success': False, 'error': 'You have already voted for this photo.'}), 400
        
        # Check if user is trying to vote for their own photo
        if photo.user_id == current_user.id:
            print(f"User trying to vote for own photo")
            return jsonify({'success': False, 'error': 'You cannot vote for your own photo.'}), 400
        
        # Create vote
        vote = Vote(user_id=current_user.id, photo_id=photo_id)
        photo.votes_count += 1
        
        db.session.add(vote)
        db.session.commit()
        
        print(f"Vote successful! New vote count: {photo.votes_count}")
        
        # Create notification
        try:
            create_notification(photo.user_id, f'Your photo "{photo.title}" received a new vote!')
        except Exception as e:
            print(f"Failed to create notification: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Vote counted successfully!',
            'votes': photo.votes_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Vote error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/comment/<int:photo_id>', methods=['POST'])
@login_required
def add_comment(photo_id):
    try:
        print(f"\n=== COMMENT ATTEMPT ===")
        print(f"User ID: {current_user.id}")
        print(f"Username: {current_user.username}")
        
        photo = Photo.query.get_or_404(photo_id)
        content = request.form.get('content')
        
        print(f"Photo: {photo.title}, Status: {photo.status}")
        print(f"Comment content length: {len(content) if content else 0}")
        
        if not content or not content.strip():
            return jsonify({'success': False, 'error': 'Comment cannot be empty.'}), 400
        
        # Check if photo is approved (or user is admin/owner)
        if photo.status != 'approved':
            if not (current_user.is_admin() or current_user.id == photo.user_id):
                return jsonify({'success': False, 'error': 'You cannot comment on this photo.'}), 403
        
        comment = Comment(
            content=content.strip(),
            user_id=current_user.id,
            photo_id=photo_id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        print(f"Comment added successfully")
        
        # Create notification
        try:
            create_notification(photo.user_id, f'Your photo "{photo.title}" has a new comment.')
        except Exception as e:
            print(f"Failed to create notification: {e}")
        
        return jsonify({
            'success': True, 
            'message': 'Comment added successfully!',
            'username': current_user.username,
            'content': content.strip()
        })
    except Exception as e:
        db.session.rollback()
        print(f"Comment error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    

# ============ ADMIN ROUTES ============

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    pending_photos = Photo.query.filter_by(status='pending').all()
    approved_photos = Photo.query.filter_by(status='approved').all()
    rejected_photos = Photo.query.filter_by(status='rejected').all()
    all_users = User.query.all()
    
    return render_template('admin.html', 
                         pending_photos=pending_photos,
                         approved_photos=approved_photos,
                         rejected_photos=rejected_photos,
                         users=all_users)

@app.route('/admin/approve/<int:photo_id>')
@login_required
@admin_required
def approve_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.status = 'approved'
    
    create_notification(photo.user_id, f'Your photo "{photo.title}" has been approved!')
    db.session.commit()
    
    flash('Photo approved successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:photo_id>')
@login_required
@admin_required
def reject_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.status = 'rejected'
    
    create_notification(photo.user_id, f'Your photo "{photo.title}" has been rejected.')
    db.session.commit()
    
    flash('Photo rejected.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/revert/<int:photo_id>')
@login_required
@admin_required
def revert_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.status = 'pending'
    
    create_notification(photo.user_id, f'Your photo "{photo.title}" has been reverted to pending status.')
    db.session.commit()
    
    flash('Photo reverted to pending.', 'info')
    return redirect(url_for('admin_dashboard'))

# ============ PROFILE UPDATE & PHOTO EDITING ROUTES ============

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    user = User.query.get(current_user.id)
    username = request.form.get('username')
    bio = request.form.get('bio', '')
    
    if username:
        # Check if username is already taken by another user
        existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
        if existing_user:
            return jsonify({'error': 'Username already taken'}), 400
        user.username = username
    
    user.bio = bio
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/edit-photo/<int:photo_id>')
@login_required
@participant_required
def edit_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if user owns the photo
    if photo.user_id != current_user.id and not current_user.is_admin():
        flash('You can only edit your own photos.', 'error')
        return redirect(url_for('profile'))
    
    # Only allow editing of pending photos
    if photo.status != 'pending':
        flash('Only pending photos can be edited.', 'error')
        return redirect(url_for('profile'))
    
    # Create form with existing data
    form = PhotoUploadForm()
    form.title.data = photo.title
    form.description.data = photo.description
    
    return render_template('edit_photo.html', form=form, photo=photo)

@app.route('/update-photo/<int:photo_id>', methods=['POST'])
@login_required
@participant_required
def update_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if user owns the photo
    if photo.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Only allow editing of pending photos
    if photo.status != 'pending':
        return jsonify({'error': 'Only pending photos can be edited'}), 400
    
    title = request.form.get('title')
    description = request.form.get('description', '')
    
    if title:
        photo.title = title
    photo.description = description
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Photo updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ============ FILE SERVING ============

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============ API ENDPOINTS ============

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                                    .order_by(Notification.created_at.desc())\
                                    .all()
    
    notifications_data = [{
        'id': n.id,
        'message': n.message,
        'time': n.created_at.strftime('%Y-%m-%d %H:%M')
    } for n in notifications]
    
    return jsonify(notifications_data)

@app.route('/api/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/leaderboard-data')
def leaderboard_data():
    top_photos = Photo.query.filter_by(status='approved')\
                           .order_by(Photo.votes_count.desc())\
                           .limit(20)\
                           .all()
    
    photos_data = [{
        'id': photo.id,
        'votes_count': photo.votes_count,
        'title': photo.title,
        'author': photo.author.username
    } for photo in top_photos]
    
    return jsonify({
        'updated': datetime.utcnow().isoformat(),
        'photos': photos_data
    })

@app.route('/api/check-auth')
def check_auth():
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'username': current_user.username if current_user.is_authenticated else None,
        'role': current_user.role if current_user.is_authenticated else None
    })

@app.route('/api/photo/<int:photo_id>')
def get_photo_details(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    return jsonify({
        'id': photo.id,
        'title': photo.title,
        'description': photo.description,
        'votes': photo.votes_count,
        'author': photo.author.username,
        'upload_date': photo.upload_date.isoformat(),
        'comments': [{
            'author': comment.commenter.username,
            'content': comment.content,
            'time': comment.created_at.strftime('%Y-%m-%d %H:%M')
        } for comment in photo.comments]
    })

@app.route('/api/test-csrf', methods=['GET'])
def test_csrf():
    return jsonify({
        'success': True,
        'message': 'CSRF endpoint works',
        'csrf_token': generate_csrf()
    })

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ============ HELPER ROUTES ============

@app.route('/clear-notifications', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/debug-user-permissions')
@login_required
def debug_user_permissions():
    return jsonify({
        'user_id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
        'is_voter': current_user.is_voter(),
        'is_participant': current_user.is_participant(),
        'is_admin': current_user.is_admin(),
        'votes_count': len(current_user.votes)
    })

@app.route('/api/debug/vote-status/<int:photo_id>')
@login_required
def debug_vote_status(photo_id):
    """Debug endpoint to check vote status for current user"""
    photo = Photo.query.get_or_404(photo_id)
    
    existing_vote = Vote.query.filter_by(user_id=current_user.id, photo_id=photo_id).first()
    
    return jsonify({
        'user_id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
        'is_voter': current_user.is_voter(),
        'photo_id': photo_id,
        'photo_title': photo.title,
        'photo_status': photo.status,
        'photo_owner': photo.user_id,
        'has_voted': existing_vote is not None,
        'can_vote': (
            current_user.is_voter() and 
            photo.status == 'approved' and 
            photo.user_id != current_user.id and 
            existing_vote is None
        )
    })
# ============ MAIN ENTRY POINT ============

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
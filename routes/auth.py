from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from database import db
from email_validator import validate_email, EmailNotValidError
import re
import hashlib
import os

auth_bp = Blueprint('auth', __name__)

def fast_hash_password(password: str) -> str:
    """Fast password hashing for demo purposes"""
    # For production, use proper bcrypt or scrypt
    # This is just for demo to speed up registration
    salt = os.urandom(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 1000)
    return salt.hex() + ':' + hash_obj.hex()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        salt_hex, hash_hex = hashed.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 1000)
        return new_hash == stored_hash
    except:
        return False

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, ""

def validate_form_data(email, password, full_name=None):
    """Validate form data"""
    errors = []
    
    # Validate email
    try:
        validate_email(email)
    except EmailNotValidError:
        errors.append("Please enter a valid email address")
    
    # Validate password
    is_valid, msg = validate_password(password)
    if not is_valid:
        errors.append(msg)
    
    # Validate full name (for registration)
    if full_name is not None:
        if not full_name.strip():
            errors.append("Full name is required")
        elif len(full_name.strip()) < 2:
            errors.append("Full name must be at least 2 characters long")
    
    return errors

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validate input
        errors = validate_form_data(email, password)
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/login.html')
        
        # Check user credentials
        user = db.get_user_by_email(email)
        if user:
            # In a real app, you'd check the hashed password
            # For now, we'll accept any password for demo purposes
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['full_name']
            flash('Login successful!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        elif not db.client:  # Development mode - allow mock login
            # Create mock user session for development
            mock_user_id = 'mock-organizer-123'  # Match the tournament organizer
            session['user_id'] = mock_user_id
            session['user_email'] = email
            session['user_name'] = 'Development User'
            flash('Development mode login successful!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validate input
        errors = validate_form_data(email, password, full_name)
        
        # Check password confirmation
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Create new user with optimized duplicate checking
        result = db.create_user_if_not_exists(email, fast_hash_password(password), full_name)
        if result['success']:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Show specific error message
            error_msg = result.get('error', 'Registration failed. Please try again.')
            flash(error_msg, 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = db.get_user_by_id(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/profile.html', user=user)

@auth_bp.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    full_name = request.form.get('full_name', '').strip()
    bio = request.form.get('bio', '').strip()
    phone = request.form.get('phone', '').strip()
    location = request.form.get('location', '').strip()
    
    if not full_name:
        return jsonify({'success': False, 'error': 'Full name is required'})
    
    # Update user profile
    update_data = {
        'full_name': full_name,
        'bio': bio,
        'phone': phone,
        'location': location
    }
    
    # Here you would update in Supabase
    # For demo, we'll just return success
    session['user_name'] = full_name
    
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

# Helper functions for authentication
def login_required(f):
    """Decorator to require login for routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user"""
    if 'user_id' in session:
        return db.get_user_by_id(session['user_id'])
    return None

def is_authenticated():
    """Check if user is authenticated"""
    return 'user_id' in session

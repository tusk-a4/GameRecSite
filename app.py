from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Game, SavedList
from config import Config
from api_client import RAWGClient
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object(Config)

# Ensure instance directory exists (only if not in serverless environment)
if not os.environ.get('VERCEL'):
    os.makedirs('instance', exist_ok=True)

db.init_app(app)

# Initialize database tables (with error handling for serverless)
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")
    # In serverless, database might not be available
    pass

# Initialize API client
api_client = RAWGClient()

@app.route('/')
def index():
    """Landing page with Login/Sign Up/Guest options"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('survey'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('signup.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        new_user = User(username=username, password_hash=password_hash)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating account. Please try again.', 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/survey', methods=['GET', 'POST'])
def survey():
    """Display recommendation survey"""
    if request.method == 'POST':
        platform = request.form.get('platform')
        genre = request.form.get('genre')
        
        if not platform or not genre:
            flash('Please select both platform and genre', 'error')
            return render_template('survey.html')
        
        # Redirect to results page
        return redirect(url_for('results', platform=platform, genre=genre))
    
    return render_template('survey.html')

@app.route('/results')
def results():
    """Display game recommendations"""
    platform = request.args.get('platform')
    genre = request.args.get('genre')
    
    if not platform or not genre:
        flash('Invalid search parameters', 'error')
        return redirect(url_for('survey'))
    
    # Try to get cached games first
    games = api_client.get_cached_games(platform, genre, limit=20)
    
    # If not enough cached games, fetch from API
    if len(games) < 10:
        api_games = api_client.get_games_by_platform_and_genre(platform, genre, page_size=20)
        if api_games:
            # Cache the new games
            api_client.cache_games_to_database(api_games)
            # Merge with cached games, avoiding duplicates
            existing_ids = {g['rawg_id'] for g in games}
            for game in api_games:
                if game['rawg_id'] not in existing_ids:
                    games.append(game)
            # Sort by rating and limit to 20
            games = sorted(games, key=lambda x: x['rating'], reverse=True)[:20]
    
    # Save to user's list if logged in
    if 'user_id' in session:
        try:
            saved_list = SavedList(
                user_id=session['user_id'],
                platform_choice=platform,
                genre_choice=genre
            )
            db.session.add(saved_list)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error saving list: {e}")
    else:
        # Store in session for guests
        if 'guest_lists' not in session:
            session['guest_lists'] = []
        session['guest_lists'].append({
            'platform': platform,
            'genre': genre,
            'timestamp': str(datetime.now())
        })
        session.modified = True
    
    return render_template('results.html', games=games, platform=platform, genre=genre)

@app.route('/my-lists')
def my_lists():
    """Display user's saved recommendation history"""
    if 'user_id' not in session:
        flash('Please login to view your lists', 'error')
        return redirect(url_for('login'))
    
    saved_lists = SavedList.query.filter_by(user_id=session['user_id']).order_by(SavedList.timestamp.desc()).all()
    
    return render_template('my_lists.html', saved_lists=saved_lists)

if __name__ == '__main__':
    app.run(debug=True)


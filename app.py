import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import requests
from flask import jsonify, request
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
# Ensure instance folder exists and use a stable DB path inside it
os.makedirs(app.instance_path, exist_ok=True)
DB_PATH = os.path.abspath(os.path.join(app.instance_path, 'houses.db'))

# ---- Database ----
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH

# --- FIXED: Use absolute path for uploads ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---- Models ----
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    houses = db.relationship('House', backref='owner', foreign_keys='House.user_id')
    # ADD THIS LINE FOR FAVORITES:
    favorite_houses = db.relationship('House', 
                                     secondary='user_favorites', 
                                     backref=db.backref('favorited_by', lazy='dynamic'),
                                     lazy='dynamic')

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    price = db.Column(db.String(20))
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    owner_phone = db.Column(db.String(50))   # NEW
    owner_email = db.Column(db.String(100))  # NEW
    bedrooms = db.Column(db.Integer, default=3)
    bathrooms = db.Column(db.Float, default=2.0)
    area_sqm = db.Column(db.Integer, default=150)
    property_type = db.Column(db.String(50), default="House")
    
    
    @property
    def price_as_float(self):
        try:
            price_str = str(self.price)
            print(f"Converting price string: '{price_str}'")
            
            # Remove € symbol if present
            price_str = price_str.replace('€', '')
            
            # Remove all commas (thousands separators)
            price_str = price_str.replace(',', '')
            
            # Remove any extra spaces
            price_str = price_str.strip()
            
            result = float(price_str)
            print(f"Converted to: {result}")
            return result
            
        except (ValueError, AttributeError) as e:
            print(f"ERROR converting '{self.price}': {e}")
            return 0.0

class HouseImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

    house = db.relationship('House', backref=db.backref('images', lazy='dynamic'))

class UserFavorites(db.Model):
    __tablename__ = 'user_favorites'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

_cached_predictor = None
def predict_price(features):
    """
    Try to call houseprice.predict_price() lazily.
    If import fails or prediction fails, return a simple fallback estimate.
    """
    global _cached_predictor
    if _cached_predictor is None:
        try:
            # try to import the project's predictor helper (lazy)
            from houseprice import predict_price as real_predict_price  # type: ignore
            _cached_predictor = real_predict_price
        except Exception:
            # fallback: simple heuristic function
            def fallback(f):
                base = 100000.0
                area = float(f.get('gr_liv_area', f.get('GrLivArea', 1500))) if f else 1500.0
                baths = float(f.get('TotalBath', f.get('total_bath', 2))) if f else 2.0
                qual = float(f.get('overall_qual', f.get('OverallQual', 5))) if f else 5.0
                return round(base + area * 100.0 + baths * 20000.0 + qual * 15000.0, 2)
            _cached_predictor = fallback
    try:
        return _cached_predictor(features)
    except Exception:
        # final fallback if predictor errors
        base = 100000.0
        area = float(features.get('gr_liv_area', 1500))
        baths = float(features.get('TotalBath', 2))
        return round(base + area * 100.0 + baths * 20000.0, 2)

# ---- Helper Functions ----
def is_logged_in():
    return 'user_id' in session and session.get('user_id') is not None

def get_current_user():
    uid = session.get('user_id')
    if uid is None:
        return None
    # Use query.filter_by to avoid legacy Query.get warning
    return User.query.filter_by(id=uid).first()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---- Routes ----
@app.route('/')
def index():
    houses = House.query.all()
    return render_template('index.html', 
                         houses=houses, 
                         search_query=None,
                         current_user=get_current_user())

@app.route('/ai_description', methods=['POST'])
def ai_description():
    data = request.get_json()

    title = data.get('title', 'Luxury Residence')
    location = data.get('location', 'a prestigious neighborhood')
    bedrooms = data.get('bedrooms', 4)
    bathrooms = data.get('bathrooms', 3)
    area = data.get('area_sqm', 250)

    prompt = f"""
You are the world's most poetic luxury real estate copywriter.
Write an irresistible, emotional, 3-sentence listing description for a {bedrooms}-bedroom, {bathrooms}-bathroom home of {area} m² called "{title}" in {location}.
Use sensory language, make the reader fall in love instantly, never mention price or square meters again after this sentence.
"""

    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        return jsonify({"description": text})
    except Exception as e:
        print("Gemini error:", e)
        # Super sexy fallback so it never breaks
        return jsonify({"description": f"Welcome to {title}, an architectural masterpiece nestled in the heart of {location}. "
                                     f"Light cascades through floor-to-ceiling windows, illuminating {bedrooms} serene bedroom retreats. "
                                     "This is where timeless elegance meets modern sophistication — your forever home awaits."})
@app.route('/add', methods=['GET', 'POST'])
def add_house():
    if not is_logged_in():
        flash('Please login to add a property', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title', '')
        location = request.form.get('location', '')
        description = request.form.get('description', '')
        bedrooms = int(request.form.get('bedrooms', 3))
        bathrooms = float(request.form.get('bathrooms', 2.0))
        area_sqm = int(request.form.get('area_sqm', 150))
        property_type = request.form.get('property_type', 'House')

        def safe_int(value, default=0):
            try:
                value = value.strip()
                return int(value) if value != '' else default
            except Exception:
                return default
        def safe_float(value, default=0.0):
            try:
                value = value.strip()
                return float(value) if value != '' else default
            except Exception:
                return default
        user_features = {
            "overall_qual": safe_int(request.form.get("overall_qual")),
            "gr_liv_area": safe_float(request.form.get("gr_liv_area")),
            "TotalBath": safe_float(request.form.get("total_bath")),
            "TotalSF": safe_float(request.form.get("total_sf")),
            "HouseAge": safe_int(request.form.get("house_age")),
            "RemodelAge": safe_int(request.form.get("remodel_age"))
        }
        user_features["OverallQual_GrLivArea"] = user_features["overall_qual"] * user_features["gr_liv_area"]

        predicted_price = predict_price(user_features)

        user_price = request.form.get('price')
        if user_price and user_price.strip() != '':
            try:
                final_price = float(user_price)
            except Exception:
                final_price = predicted_price
        else:
            final_price = predicted_price

        # --- FIXED: save image with secure filename ---
        image_file = request.files.get('image')
        filename = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        house = House(
            title=title,
            price=str(final_price),
            location=location,
            description=description,
            image=filename,
            user_id=session.get('user_id'),
            owner_phone=request.form.get('owner_phone'),      # NEW
            owner_email=request.form.get('owner_email'),       # NEW
            bedrooms=request.form.get('bedrooms'),
            bathrooms=request.form.get('bathrooms'),
            area_sqm=request.form.get('area_sqm'),
            property_type=request.form.get('property_type')
        )

        db.session.add(house)
        db.session.commit()

          # ---- Save optional interior images ----
        interior_files = request.files.getlist('interior_images')
        interior_filenames = []
        for file in interior_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                interior_filenames.append(filename)

                # Save in DB
                interior_img = HouseImage(house_id=house.id, filename=filename)
                db.session.add(interior_img)

        db.session.commit()  # commit interior images

        flash(f'Property added successfully! Predicted price was ${predicted_price:,.2f}', 'success')
        return redirect(url_for('index'))

    return render_template('add_house.html', current_user=get_current_user())

@app.route('/house/<int:id>')
def view_house(id):
    house = House.query.get_or_404(id)
    interior_images = HouseImage.query.filter_by(house_id=house.id).all()
    # Fetch a few other houses to show as "similar"
    similar_houses = House.query.filter(House.id != id).limit(3).all()
    
    return render_template('house.html', 
                           house=house, 
                           interior_images=interior_images, 
                           similar_houses=similar_houses, 
                           current_user=get_current_user())

# ---- Authentication Routes ----
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Show login page even if session exists; only redirect when already logged-in user requests it intentionally
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Login successful
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    else:
        # If there's an existing session that points to a missing user, clear it to avoid redirect loops
        if session.get('user_id') is not None and User.query.filter_by(id=session.get('user_id')).first() is None:
            session.clear()
    return render_template('login.html', current_user=get_current_user())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            is_admin=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', current_user=get_current_user())

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    try:
        user = get_current_user()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('login'))
            
        user_houses = House.query.filter_by(user_id=user.id).all()
        
        # Get user's favorite houses
        favorite_houses = user.favorite_houses.all()
        
        return render_template('profile.html', 
                              current_user=user, 
                              user_houses=user_houses,
                              favorite_houses=favorite_houses)
    
    except Exception as e:
        print(f"Error in profile route: {e}")
        flash('An error occurred while loading your profile', 'danger')
        return redirect(url_for('index'))
    

# ---- Favorites Routes ----
@app.route('/is_favorite/<int:house_id>')
def is_favorite(house_id):
    if not is_logged_in():
        return jsonify({'is_favorite': False})
    
    user = get_current_user()
    if not user:
        return jsonify({'is_favorite': False})
    
    try:
        # Check if house is in user's favorites
        for favorite in user.favorite_houses:
            if favorite.id == house_id:
                return jsonify({'is_favorite': True})
        return jsonify({'is_favorite': False})
    except Exception as e:
        print(f"Error checking favorite: {e}")
        return jsonify({'is_favorite': False})

@app.route('/add_favorite/<int:house_id>', methods=['POST'])
def add_favorite(house_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Please login to add favorites'})
    
    try:
        house = House.query.get(house_id)
        if not house:
            return jsonify({'success': False, 'message': 'Property not found'})
        
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Check if already favorited
        for favorite in user.favorite_houses:
            if favorite.id == house_id:
                return jsonify({'success': False, 'message': 'Already in favorites'})
        
        user.favorite_houses.append(house)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Added to favorites'})
    
    except Exception as e:
        print(f"Error adding favorite: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error adding to favorites'})

@app.route('/remove_favorite/<int:house_id>', methods=['POST'])
def remove_favorite(house_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Please login'})
    
    try:
        house = House.query.get(house_id)
        if not house:
            return jsonify({'success': False, 'message': 'Property not found'})
        
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Find and remove the favorite
        for favorite in user.favorite_houses:
            if favorite.id == house_id:
                user.favorite_houses.remove(favorite)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Removed from favorites'})
        
        return jsonify({'success': False, 'message': 'Not in favorites'})
    
    except Exception as e:
        print(f"Error removing favorite: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error removing from favorites'})

# ---- Prediction API Route ----
@app.route('/predict_price', methods=['POST'])
def predict_price_api():
    try:
        data = request.get_json() or {}
        user_features = {
            "overall_qual": int(float(data.get("overall_qual", 0))) if data.get("overall_qual") is not None else 0,
            "gr_liv_area": float(data.get("gr_liv_area", 0)) if data.get("gr_liv_area") is not None else 0.0,
            "TotalBath": float(data.get("total_bath", 0)) if data.get("total_bath") is not None else 0.0,
            "TotalSF": float(data.get("total_sf", 0)) if data.get("total_sf") is not None else 0.0,
            "HouseAge": int(float(data.get("house_age", 0))) if data.get("house_age") is not None else 0,
            "RemodelAge": int(float(data.get("remodel_age", 0))) if data.get("remodel_age") is not None else 0,
        }
        user_features["OverallQual_GrLivArea"] = user_features["overall_qual"] * user_features["gr_liv_area"]
        predicted_price = predict_price(user_features)
        return jsonify({'predicted_price': round(float(predicted_price), 2)})
    except Exception as e:
        app.logger.exception("Error in predict_price_api")
        return jsonify({'error': str(e)})

# ---- Delete Property Route ----
@app.route('/delete_house/<int:id>', methods=['POST'])
@login_required
def delete_house(id):
    house = House.query.get_or_404(id)
    
    # Check if the current user owns the house or is admin
    user = get_current_user()
    if house.user_id != user.id and not user.is_admin:
        flash('You can only delete your own properties!', 'danger')
        return redirect(url_for('profile'))
    
    try:
        # Delete associated favorites first (due to foreign key constraints)
        UserFavorites.query.filter_by(house_id=id).delete()
        
        # Delete associated images (HouseImage records)
        HouseImage.query.filter_by(house_id=id).delete()
        
        # Delete the house
        db.session.delete(house)
        # After db.session.delete(house)
        if house.image:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], house.image))
        for img in house.images:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img.filename))
        db.session.commit()
        
        flash('Property deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting property. Please try again.', 'danger')
        print(f"Error deleting house: {e}")
    
    return redirect(url_for('profile'))

# ---- Reset Database Route (dev only) ----
@app.route('/reset-db')
def reset_db():
    if app.debug:
        with app.app_context():
            db.drop_all()
            init_db()
        flash('Database has been reset with sample data', 'success')
        return redirect(url_for('index'))
    else:
        flash('Database reset is only available in debug mode', 'danger')
        return redirect(url_for('index'))

@app.route('/reset-favorites')
def reset_favorites():
    if app.debug:  # Only in debug mode
        try:
            with app.app_context():
                # Drop all tables
                db.drop_all()
                # Recreate all tables with new schema
                db.create_all()
                
                # Create admin user
                admin_user = User(
                    username='admin',
                    email='admin@renthomes.com',
                    password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.flush()
                
                # Add sample houses
                sample_houses = [
                    House(
                        title="Ocean Breeze Villa",
                        price="910000.00",
                        location="Santorini, Greece",
                        description="Stunning oceanfront villa with private beach access, infinity pool, and 5 bedrooms.",
                        image="",
                        user_id=admin_user.id,
                        owner_phone="+30 210 1234567",
                        owner_email=admin_user.email,
                        bedrooms=5,
                        bathrooms=4,
                        area_sqm=350
                    ),
                    House(
                        title="Jatson House",
                        price="750000.00",
                        location="London, UK",
                        description="Historic townhouse in central London with modern amenities.",
                        image="https://images.unsplash.com/photo-1518780664697-55e3ad937233?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80",
                        user_id=admin_user.id,
                        owner_phone="+44 20 7946 0958",
                        owner_email=admin_user.email,
                        bedrooms=4,
                        bathrooms=3,
                        area_sqm=280
                    ),
                    House(
                        title="Lakeside Cottage",
                        price="540000.00",
                        location="Interlaken, Switzerland",
                        description="Cozy cottage with lake view and direct access to hiking trails.",
                        image="https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80",
                        user_id=admin_user.id,
                        owner_phone="+41 33 123 4567",
                        owner_email=admin_user.email,
                        bedrooms=3,
                        bathrooms=2,
                        area_sqm=150
                    ),
                    House(
                        title="Mountain Retreat",
                        price="620000.00",
                        location="Aspen, Colorado",
                        description="Modern mountain home with panoramic views, ski-in/ski-out access, and luxury amenities.",
                        image="",
                        user_id=admin_user.id,
                        owner_phone="+1 970 555 1234",
                        owner_email=admin_user.email,
                        bedrooms=4,
                        bathrooms=3,
                        area_sqm=320
                    ),
                    House(
                        title="Urban Loft",
                        price="850000.00",
                        location="New York, NY",
                        description="Industrial chic loft in trendy SoHo neighborhood with exposed brick, high ceilings, and premium finishes.",
                        image="",
                        user_id=admin_user.id,
                        owner_phone="+1 212 555 6789",
                        owner_email=admin_user.email,
                        bedrooms=2,
                        bathrooms=2,
                        area_sqm=180
                    ),
                    House(
                        title="Beachfront Paradise",
                        price="1200000.00",
                        location="Miami, Florida",
                        description="Luxury beachfront condo with ocean views, private balcony, and resort-style amenities.",
                        image="",
                        user_id=admin_user.id,
                        owner_phone="+1 305 555 2468",
                        owner_email=admin_user.email,
                        bedrooms=3,
                        bathrooms=2,
                        area_sqm=200
                )

                ]
                for house in sample_houses:
                    db.session.add(house)
                
                db.session.commit()
                flash('Database reset with favorites support!', 'success')
        except Exception as e:
            flash(f'Error resetting database: {str(e)}', 'danger')
        
        return redirect(url_for('index'))
    else:
        flash('Reset only available in debug mode', 'danger')
        return redirect(url_for('index'))

# ---- Initialize Database ----
def init_db():
    with app.app_context():
        # Create tables if missing
        db.create_all()
        # Seed admin + sample houses only when no users exist
        if User.query.first() is None:
            admin_user = User(
                username='admin',
                email='admin@renthomes.com',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.flush()
            sample_houses = [
                House(
                    title="Ocean Breeze Villa",
                    price="910000.00",
                    location="Santorini, Greece",
                    description="Stunning oceanfront villa with private beach access, infinity pool, and 5 bedrooms.",
                    image="",
                    user_id=admin_user.id,
                    owner_phone="+30 22860 12345",
                    owner_email=admin_user.email,
                    bedrooms=5,
                    bathrooms=4,
                    area_sqm=350
                ),
                House(
                    title="Jatson House",
                    price="750000.00",
                    location="London, UK",
                    description="Historic townhouse in central London with modern amenities.",
                    image="",
                    user_id=admin_user.id,
                    owner_phone="+44 20 7946 0958",
                    owner_email=admin_user.email,
                    bedrooms=4,
                    bathrooms=3,
                    area_sqm=250
                ),
                House(
                    title="Lakeside Cottage",
                    price="540000.00",
                    location="Interlaken, Switzerland",
                    description="Cozy cottage with lake view and direct access to hiking trails.",
                    image="",
                    user_id=admin_user.id,
                    owner_phone="+41 33 822 1234",
                    owner_email=admin_user.email,
                    bedrooms=3,
                    bathrooms=2,
                    area_sqm=180
                )
            ]
            for house in sample_houses:
                db.session.add(house)
            db.session.commit()
            print("Database initialized with sample data")
        else:
            print("Database already contains users; skipping sample data")
# ---- Search Route ----# ---- Search Route ----
@app.route('/search')
def search():
    # Get search parameters
    city = request.args.get('city', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    
    print(f"\n=== DEBUG SEARCH ===")
    print(f"City: '{city}', Min: '{min_price}', Max: '{max_price}'")
    
    # Start with all houses
    houses = House.query.all()
    print(f"Total houses: {len(houses)}")
    
    # Apply city filter
    if city:
        houses = [h for h in houses if city.lower() in h.location.lower()]
        print(f"After city filter: {len(houses)} houses")
    
    # Debug: print all house prices before filtering
    print("\nAll houses before price filter:")
    for h in houses:
        print(f"  ID {h.id}: '{h.title}' - Price string: '{h.price}' - as_float: {h.price_as_float}")
    
    # Apply price filters
    if min_price:
        try:
            # Remove comma from min_price if present
            min_price_clean = min_price.replace(',', '')
            min_price_val = float(min_price_clean)
            print(f"\nApplying MIN filter: >= {min_price_val}")
            
            before_count = len(houses)
            houses = [h for h in houses if h.price_as_float >= min_price_val]
            
            print(f"Filtered from {before_count} to {len(houses)} houses")
            
        except ValueError:
            flash('Invalid minimum price', 'warning')
    
    if max_price:
        try:
            # Remove comma from max_price if present
            max_price_clean = max_price.replace(',', '')
            max_price_val = float(max_price_clean)
            print(f"\nApplying MAX filter: <= {max_price_val}")
            
            before_count = len(houses)
            houses = [h for h in houses if h.price_as_float <= max_price_val]
            
            print(f"Filtered from {before_count} to {len(houses)} houses")
            print("Remaining houses:")
            for h in houses:
                print(f"  ID {h.id}: '{h.title}' - Price: {h.price_as_float}")
            
        except ValueError:
            flash('Invalid maximum price', 'warning')
    
    # Build search query description
    search_parts = []
    if city:
        search_parts.append(f'location: {city}')
    if min_price:
        search_parts.append(f'min price: €{min_price}')
    if max_price:
        search_parts.append(f'max price: €{max_price}')
    
    search_query = ', '.join(search_parts) if search_parts else None
    
    print(f"\nFinal results: {len(houses)} houses")
    print("=== END DEBUG ===\n")
    
    return render_template('index.html', 
                         houses=houses, 
                         search_query=search_query,
                         current_user=get_current_user())

@app.route('/test-prices')
def test_prices():
    houses = House.query.all()
    result = []
    for house in houses:
        result.append({
            'id': house.id,
            'title': house.title,
            'raw_price': repr(house.price),  # Shows exact string with quotes
            'price_string': house.price,
            'price_as_float': house.price_as_float,
            'location': house.location
        })
    return jsonify(result)

# Add this route after your other routes
@app.route('/debug-prices')
def debug_prices():
    houses = House.query.all()
    results = []
    for house in houses:
        results.append({
            'id': house.id,
            'title': house.title,
            'price_string': house.price,
            'price_as_float': house.price_as_float,
            'location': house.location
        })
    return jsonify(results)


# ---- Setup Database ----
def setup_database():
    # If DB exists, ensure tables and leave data alone; otherwise create and seed
    if os.path.exists(DB_PATH):
        print(f"Database already exists at {DB_PATH}. Leaving it unchanged.")
        # ensure tables exist
        with app.app_context():
            db.create_all()
        return True

    try:
        init_db()
        print("New database created successfully")
        return True
    except Exception as e:
        print(f"Error creating new database: {e}")
        return False

if __name__ == '__main__':
    if setup_database():
        app.run(debug=True)
    else:
        print("Failed to setup database. Please check permissions and try again.")
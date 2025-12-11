# SweetHomes: AI-Powered Real Estate Marketplace & Price Predictor

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-black)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**SweetHomes** is a modern, full-stack web application that serves as a real estate marketplace where users can upload, browse, search, and manage property listings. It features AI-powered property descriptions generated via Google Gemini API and house price predictions using an XGBoost model trained on the Ames Housing dataset. The app emphasizes user-friendly design with responsive UI, secure authentication, and interactive features like favoriting properties and contact info toggles.

This project was built to explore web development with Flask, AI integration (Gemini for descriptions), machine learning for predictions (XGBoost via scikit-learn and Hugging Face datasets), and database management with SQLAlchemy.

## Key Features

- **User Authentication**: Secure registration, login, and session management with password hashing (Werkzeug). Profile pages show owned properties and favorites.
- **Property Management**: Users can add new properties with multi-image uploads (main + interiors), auto-generated luxury descriptions via Gemini AI, and AI-predicted prices.
- **Search & Filtering**: Advanced search by city, min/max price with real-time formatting. Results display with clear summaries and clear-search buttons.
- **Property Details**: Detailed views with image galleries (thumbnails, swapping), features list, and toggleable owner contact info.
- **Favorites System**: Users can add/remove favorites with AJAX updates and heart icon toggles.
- **AI Price Prediction**: XGBoost model predicts prices based on features like overall quality, living area, baths, total SF, house/remodel age. Fallback to simple estimates if ML fails.
- **AI Descriptions**: Gemini generates engaging, luxury-style property descriptions from basic inputs (title, location, beds/baths/area).
- **Responsive Design**: Glassmorphic UI with dark mode toggle (localStorage), smooth animations (IntersectionObserver), and mobile-friendly layouts.
- **Admin/Owner Controls**: Owners can delete their listings with confirmation modals.
- **Debug Tools**: Routes like `/debug-prices` and `/test-prices` for price conversion troubleshooting.

## Tech Stack

- **Backend**: Python 3.8+, Flask (routing, templates), SQLAlchemy (SQLite DB), Werkzeug (security).
- **Frontend**: HTML5, CSS3 (glassmorphism, gradients), JavaScript (DOM manipulation, async fetches).
- **AI/ML**: Google Gemini API (descriptions), XGBoost (price prediction via scikit-learn), Pandas/Numpy (data handling), Hugging Face datasets (Ames Housing for training).
- **Other**: Font Awesome (icons), Unsplash placeholders (images), dotenv (env vars), secure file uploads.

## Screenshots

### Home Page with Search
![Home Page]<img width="1919" height="1004" alt="Screenshot 2025-12-11 111232" src="https://github.com/user-attachments/assets/10a52ff9-60bf-41cd-ae8e-81e6015bb09e" />
-home.png) <img width="1919" height="997" alt="Screenshot 2025-12-11 111242" src="https://github.com/user-attachments/assets/d3c27678-657e-4509-817f-2a0f6dea0cb0" />


### Property Upload Form
![Add Property]<img width="1919" height="1002" alt="Screenshot 2025-12-11 111327" src="https://github.com/user-attachments/assets/3f681c25-5186-4cbf-9a94-692d867ecbb3" />
<img width="1919" height="1003" alt="Screenshot 2025-12-11 111316" src="https://github.com/user-attachments/assets/8e701878-0c86-4dff-a6fa-93c607839e54" />
<img width="1919" height="1002" alt="Screenshot 2025-12-11 111336" src="https://github.com/user-attachments/assets/df71d4e5-fee4-4c1e-a098-688821a66a91" />


### Property Detail View
![Property Details]<img width="1919" height="1004" alt="Screenshot 2025-12-11 111421" src="https://github.com/user-attachments/assets/0ac87dfa-4f14-418b-8f07-b982a167d660" />
<img width="1919" height="997" alt="Screenshot 2025-12-11 111431" src="https://github.com/user-attachments/assets/e1d44334-761a-463c-8fc2-78dee3aab538" />


### User Profile
![Profile]<img width="1919" height="1001" alt="Screenshot 2025-12-11 111356" src="https://github.com/user-attachments/assets/1e89c23e-b248-4761-b25e-d6f6a85b639e" />
<img width="1919" height="1003" alt="Screenshot 2025-12-11 111406" src="https://github.com/user-attachments/assets/93bffb88-12ab-4624-827f-1d104695643b" />


### Login/Register (Glassmorphic)
![Auth]
<img width="1919" height="1001" alt="Screenshot 2025-12-11 111451" src="https://github.com/user-attachments/assets/a8109cf7-fbe8-49ca-982b-6ee40f0e50c9" />
<img width="1919" height="1001" alt="Screenshot 2025-12-11 111502" src="https://github.com/user-attachments/assets/a39c10b8-4200-4b49-a32e-32879fcb7c69" />

## Installation

1. **Clone the Repository**:
   ```
   git clone https://github.com/me-r1em/SweetHomes-Real-Estate-Price-Prediction-Property-Marketplace.git
   cd SweetHomes-Real-Estate-Price-Prediction-Property-Marketplace
   ```

2. **Set Up Virtual Environment**:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```
   *Note: If no requirements.txt, install manually: `pip install flask flask-sqlalchemy werkzeug xgboost pandas numpy scikit-learn google-generativeai python-dotenv`*

4. **Configure Environment**:
   - Create `.env` file in root:
     ```
     FLASK_SECRET_KEY=your_secret_key_here  # Generate with secrets.token_hex(32)
     GEMINI_API_KEY=your_gemini_api_key_here  # From Google AI Studio
     ```

5. **Initialize Database**:
   - Run `app.py` once – it auto-creates `instance/houses.db` and seeds if needed.

## Usage

1. **Run the App**:
   ```
   python app.py
   ```
   - Access at `http://localhost:5000`
   - Debug mode enabled (`debug=True`).

2. **Key Routes**:
   - `/`: Home with search and listings.
   - `/add_house`: Upload new property (requires login).
   - `/house/<id>`: View property details.
   - `/profile`: User dashboard with owned/favorite properties.
   - `/login` & `/register`: Auth pages.
   - `/predict_price`: API endpoint for AI predictions (POST JSON with features).
   - `/ai_description`: API for Gemini descriptions (POST JSON with property data).
   - `/debug-prices`: JSON debug for price conversions.

3. **Testing Predictions**:
   - In add_house form, fill ML fields and click "Use AI to Predict Price".
   - Or POST to `/predict_price`:
     ```json
     {
       "overall_qual": 7,
       "gr_liv_area": 1800,
       "total_bath": 2.5,
       "total_sf": 2800,
       "house_age": 15,
       "remodel_age": 10
     }
     ```

4. **Generating Descriptions**:
   - Click "Generate Luxury Description with AI" in add form.
   - Or POST to `/ai_description`.

## Development Notes

- **Database**: SQLite (`instance/houses.db`). Models: User, House, HouseImage, UserFavorites.
- **Images**: Uploaded to `static/uploads/`. Placeholders from Unsplash for missing images.
- **Price Handling**: Robust conversion (removes €/commas/spaces) in `House.price_as_float`.
- **Security**: File uploads secured (`secure_filename`), max size 16MB.
- **AI Fallbacks**: If Gemini fails, default to basic descriptions. ML uses pre-trained XGBoost on Ames data.
- **Dark Mode**: Toggles via JS/localStorage, with CSS overrides.

## Contributing

1. Fork the repo.
2. Create feature branch: `git checkout -b feature/AmazingFeature`.
3. Commit changes: `git commit -m 'Add some AmazingFeature'`.
4. Push: `git push origin feature/AmazingFeature`.
5. Open Pull Request.

Please follow code style (PEP8) and add tests where possible.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Ames Housing Dataset via Hugging Face.
- Google Gemini for AI descriptions.
- Flask community for robust web framework.
- Unsplash for placeholder images.

Questions? Open an issue or contact [merad.meriem.chehd@gmail.com]. Happy house hunting! 🏠✨

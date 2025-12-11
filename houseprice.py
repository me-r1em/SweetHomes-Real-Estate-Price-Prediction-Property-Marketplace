#pandas & numpy: data manipulation
import pandas as pd
import numpy as np
#sklearn: preprocessing (scaling, encoding), model utilities
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
#xgboost: powerful gradient boosting model for regression
from xgboost import XGBRegressor

# ============================================================
# 1. Load Dataset the famous Ames Housing Dataset (used for house price prediction) directly from Hugging Face
# ============================================================
data = pd.read_csv(
    "https://huggingface.co/datasets/cloderic/ames_iowa_housing/resolve/main/AmesHousing.csv"
)

# ============================================================
# 2. Feature Engineering
# ============================================================
data['HouseAge'] = data['yr_sold'] - data['year_built']
data['RemodelAge'] = data['yr_sold'] - data['year_remod_add']
data['TotalBath'] = data['full_bath'] + 0.5 * data['half_bath']
data['TotalSF'] = data['gr_liv_area'] + data['total_bsmt_sf']
data['OverallQual_GrLivArea'] = data['overall_qual'] * data['gr_liv_area']

# ============================================================
# 3. Features / Target
# ============================================================
#X: all columns except price
X = data.drop("saleprice", axis=1)
#y: log-transformed sale price (common practice to stabilize variance and improve model performance)
y = np.log1p(data["saleprice"])

# Column types
#Automatically detects which columns are numeric vs categorical (strings)
numeric_cols = X.select_dtypes(include=["int64", "float64"]).columns
categorical_cols = X.select_dtypes(include=["object"]).columns

# ============================================================
# 4. Preprocessing Pipeline
# ============================================================
# Numeric: Standard Scaling
#Scales numeric features (mean=0, std=1)
numeric_transformer = StandardScaler()
# Categorical: One-Hot Encoding
#Encodes categorical features as one-hot vectors
categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_cols),
        ('cat', categorical_transformer, categorical_cols)
    ]
)
# Fit and transform the data
# Output: preprocessed feature matrix
# Outputs dense NumPy array (not sparse)
X_preprocessed = preprocessor.fit_transform(X)

# ============================================================
# 5. Train Model
# ============================================================
xgb_model = XGBRegressor(
    #tree parameters
    n_estimators=800,
    #learning parameters (slow learning rate for better performance)
    learning_rate=0.03,
    #regularization parameters (reg_alpha, reg_lambda) prevents overfitting
    max_depth=6,
    #Subsampling reduces variance
    subsample=0.85,
    #Feature subsampling (colsample_bytree) reduces correlation between trees
    colsample_bytree=0.85,
    #regularization terms (L1 and L2)
    reg_alpha=0.5,
    reg_lambda=1.0,
    #Loss function for regression
    objective='reg:squarederror',
    #Random seed for reproducibility
    random_state=42
)
#Train model
#Trained on log(price), so predictions will be in log scale
xgb_model.fit(X_preprocessed, y)

# ============================================================
# 6. PREDICTION FUNCTION (USED BY FLASK)
# ============================================================
#Core function used by Flask app to predict price from form input
def predict_price(input_dict):
    """
    input_dict = dictionary of user inputs
    Example:
      {
        "overall_qual": 7,
        "gr_liv_area": 1800,
        "TotalBath": 2.5,
        ...
      }
    """

    # Create an empty row with correct columns
    row = pd.DataFrame(columns=X.columns)
    row.loc[0] = 0

    # Fill categorical defaults
    for col in categorical_cols:
        row[col] = "None"

    # Fill numeric defaults
    for col in numeric_cols:
        row[col] = 0.0

    # Apply user values
    for key, value in input_dict.items():
        if key in row.columns:
            row.at[0, key] = value
        else:
            print(f"[WARNING] Column '{key}' not in dataset")

    # Preprocess row
    processed = preprocessor.transform(row)

    # Predict
    log_price = xgb_model.predict(processed)[0]
    price = np.expm1(log_price)

    return float(price)

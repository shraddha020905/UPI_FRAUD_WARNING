import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import os

# 1️⃣ Load dataset
data = pd.read_csv("../datasets/transactions.csv")

# 2️⃣ Encode categorical feature 'payee_name'
le_name = LabelEncoder()
data['payee_name_enc'] = le_name.fit_transform(data['payee_name'])

# 3️⃣ Prepare features and labels
X = data[['amount', 'payee_name_enc']]
y = data['label']

# 4️⃣ Split dataset into training and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 5️⃣ Train Random Forest model
model = RandomForestClassifier(n_estimators=50, random_state=42)
model.fit(X_train, y_train)

# 6️⃣ Save model and encoder in backend folder
backend_folder = os.path.dirname(os.path.abspath(__file__))
joblib.dump(model, os.path.join(backend_folder, "fraud_model.pkl"))
joblib.dump(le_name, os.path.join(backend_folder, "payee_encoder.pkl"))

print("Model trained and saved in backend folder!")



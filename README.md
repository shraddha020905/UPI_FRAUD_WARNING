UPI Fraud Warning Assistant is a full-stack project that helps users detect potential UPI frauds through transaction risk analysis and SMS scam detection.

Features

Transaction Fraud Detection

Analyzes UPI transactions using a machine learning model.

Inputs: User ID, Payee Name, Payee VPA, Amount, Timestamp.

Outputs: Risk Score, Risk Level (Low/Medium/High), and reasons for suspicion.

SMS Fraud Detection

Hybrid approach combining rule-based keyword detection and ML prediction.

Detects phishing, scam, and fraudulent messages related to UPI, wallets, KYC, bills, and more.

Outputs: Prediction (Spam/Fraud or Safe), Confidence score, and user-friendly warning.

Interactive Frontend

Easy-to-use HTML/CSS/JS interface.

Mobile-friendly and responsive.

Dynamic risk meters and color-coded warnings.

Tech Stack

Frontend: HTML, CSS, JavaScript

Backend: Python, FastAPI

Machine Learning: scikit-learn, pandas, numpy

Deployment: Localhost (can be extended to cloud servers)

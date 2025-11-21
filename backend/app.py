# app.py  — hardened version (drop-in)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
import os

app = FastAPI(title="UPI Fraud Warning API")

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("upi-fraud-api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input models
class Transaction(BaseModel):
    user_id: str
    payee_name: str
    payee_vpa: Optional[str] = None
    amount: float
    timestamp: str

class SMSMessage(BaseModel):
    text: str

# Globals for models (populated in startup)
model = None
encoder = None
sms_model = None
sms_vectorizer = None
MODEL_FEATURES = None

MODEL_FILES = {
    "model": "fraud_model.pkl",
    "encoder": "payee_encoder.pkl",
    "sms_model": "sms_model.pkl",
    "sms_vectorizer": "sms_vectorizer.pkl"
}

@app.on_event("startup")
def load_models_at_startup():
    global model, encoder, sms_model, sms_vectorizer, MODEL_FEATURES
    # Ensure files exist
    missing = [fname for fname in MODEL_FILES.values() if not os.path.exists(fname)]
    if missing:
        msg = f"Model files missing: {missing}. Put them in the same folder as app.py or set path correctly."
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        model = joblib.load(MODEL_FILES["model"])
        encoder = joblib.load(MODEL_FILES["encoder"])
        sms_model = joblib.load(MODEL_FILES["sms_model"])
        sms_vectorizer = joblib.load(MODEL_FILES["sms_vectorizer"])
        # feature_names_in_ might be a numpy array; cast to list
        MODEL_FEATURES = list(getattr(model, "feature_names_in_", []))
        logger.info("Models loaded successfully.")
    except Exception as e:
        logger.exception("Failed loading models:")
        raise

@app.get("/health")
def health():
    ok = model is not None and encoder is not None and sms_model is not None and sms_vectorizer is not None
    return {"status": "ok" if ok else "error", "models_loaded": ok}

@app.get("/")
def read_root():
    return {"message": "UPI Fraud Warning Backend is running!"}

@app.post("/predict")
def predict(transaction: Transaction):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded on server.")
    try:
        df = pd.DataFrame([{
            "user_id": transaction.user_id,
            "payee_name": transaction.payee_name,
            "payee_vpa": transaction.payee_vpa or "",
            "amount": transaction.amount,
            "timestamp": transaction.timestamp
        }])

        # safe encoder transform: if encoder is a sklearn LabelEncoder/OrdinalEncoder,
        # unknown labels may raise. We'll fallback to -1 for unknowns.
        try:
            # encoder.transform might expect 1D array-like
            enc = encoder.transform(df["payee_name"])
            df["payee_name_enc"] = enc
        except Exception:
            logger.warning("encoder.transform failed for given payee_name(s); using fallback -1")
            df["payee_name_enc"] = [-1] * len(df)

        # Build input X following model's feature names if possible
        X_dict = {}
        for col in MODEL_FEATURES:
            if col in df.columns:
                X_dict[col] = df[col]
            elif col == "payee_name_enc" and "payee_name_enc" in df.columns:
                X_dict[col] = df["payee_name_enc"]
            elif col == "amount" and "amount" in df.columns:
                X_dict[col] = df["amount"]
            else:
                # fill defaults with zeros
                X_dict[col] = 0

        X = pd.DataFrame(X_dict)

        # predict_proba safety
        if hasattr(model, "predict_proba"):
            risk_prob = model.predict_proba(X)[0][1]
        else:
            # fallback to predict for classifiers without predict_proba
            pred = model.predict(X)[0]
            risk_prob = float(pred)

        risk_prob = float(np.clip(risk_prob, 0, 1))

        if risk_prob > 0.7:
            risk_level = "High"
            color = "red"
        elif risk_prob > 0.4:
            risk_level = "Medium"
            color = "orange"
        else:
            risk_level = "Low"
            color = "green"

        reasons = []
        if transaction.amount > 1000:
            reasons.append("High transaction amount")
        if "support" in transaction.payee_name.lower():
            reasons.append("Suspicious payee name (possible scam)")
        if risk_level == "High":
            reasons.append("Machine learning model flagged this transaction")
        if not reasons:
            reasons.append("No obvious risk factors detected")

        return {
            "risk_score": round(risk_prob, 2),
            "risk_level": risk_level,
            "color": color,
            "reasons": reasons
        }
    except Exception as e:
        logger.exception("Error during /predict:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-sms")
def detect_sms(data: SMSMessage):
    try:
        msg = (data.text or "").lower()
        reasons = []
        suspicious_keywords = [
            "urgent", "immediately", "block", "verification", "otp",
            "kbc", "lottery", "support", "click", "link", "refund",
            "account suspended", "reward", "free"
        ]
        for word in suspicious_keywords:
            if word in msg:
                reasons.append(f"Contains suspicious keyword: '{word}'")
        risk_score = min(len(reasons) * 0.2, 1.0)
        risk_level = ("High" if risk_score > 0.7 else "Medium" if risk_score > 0.4 else "Low")
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "reasons": reasons if reasons else ["No suspicious pattern found"]
        }
    except Exception as e:
        logger.exception("Error during /detect-sms:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict_sms")
def predict_sms(message: SMSMessage):
    if sms_model is None or sms_vectorizer is None:
        raise HTTPException(status_code=500, detail="SMS model not loaded")
    try:
        text = (message.text or "").lower()

        # simplified keyword bank (keeps your lists)
        upi_keywords = [
            "approve request", "approval required", "approve to receive",
            "request money", "collect request", "upi id disabled",
            "upi verification", "upi reactivate", "upi blocked",
            "upi pin", "pending refund", "payment request"
        ]
        wallet_keywords = [
            "wallet suspended", "wallet blocked", "paytm wallet", "phonepe wallet",
            "gpay wallet", "wallet locked", "wallet disabled"
        ]
        pan_aadhaar_keywords = [
            "pan will be deactivated", "pan deactivated", "update pan", "link pan",
            "aadhaar", "aadhar", "aadhaar update", "aadhaar not verified", "link aadhaar",
            "aadhaar kyc", "pan kyc", "id verification"
        ]
        bill_keywords = [
            "electricity bill", "bill overdue", "power disconnected", "disconnected tonight",
            "delivery failed", "customs", "customs fee", "parcel", "shipment on hold",
            "address verification", "courier", "pay to release"
        ]
        legal_keywords = [
            "late emi", "legal action", "final notice", "penalty", "overdue", "recovery team",
            "court notice", "summons"
        ]
        urgent_phrases = [
            "verify immediately", "verify now", "update now", "complete kyc",
            "complete verification", "verify your account", "restore access",
            "reactivate", "update your account"
        ]
        job_scam_keywords = [
            "job shortlisted", "profile shortlisted", "registration fee",
            "pay registration", "interview fee", "training fee",
            "job offer", "job vacancy", "immediate joining",
            "government job", "govt job", "apply now"
        ]
        strong_phrases = [
            "pay to continue", "urgent fee", "processing fee",
            "small fee", "to schedule interview", "click to verify",
            "click to apply", "click here to continue"
        ]

        all_keywords = (
            upi_keywords + wallet_keywords + pan_aadhaar_keywords +
            bill_keywords + legal_keywords + urgent_phrases +
            job_scam_keywords + strong_phrases
        )

        rule_hits = [kw for kw in all_keywords if kw in text]
        rule_score = min(len(rule_hits) * 0.22, 1.0)

        # ML prediction safe
        try:
            vec = sms_vectorizer.transform([message.text])
            ml_prob = float(sms_model.predict_proba(vec)[0][1]) if hasattr(sms_model, "predict_proba") else float(sms_model.predict(vec)[0])
        except Exception:
            logger.exception("sms model/vectorizer prediction failed; defaulting ml_prob=0.0")
            ml_prob = 0.0

        final_score = max(rule_score, ml_prob)

        if final_score >= 0.40:
            prediction = "Spam / Fraud"
            user_message = "🚨 This message is a scam. Ignore it completely."
        else:
            prediction = "Safe"
            user_message = "✅ You're good to go. This message looks safe."

        return {
            "prediction": prediction,
            "probability": round(final_score, 2),
            "message": user_message,
            "rule_hits": rule_hits
        }
    except Exception as e:
        logger.exception("Error during /predict_sms:")
        raise HTTPException(status_code=500, detail=str(e))


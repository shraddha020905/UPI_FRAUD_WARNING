// ==============================
// ⚡ BASE URL — change depending on environment
// ==============================

// PC browser: use localhost
// Android emulator: use 10.0.2.2
// Real phone: use your PC LAN IP, e.g., 192.168.1.8
const BASE_URL = "http://127.0.0.1:8000";

// ==============================
// PAGE NAVIGATION
// ==============================
function showSMSChecker() {
    document.getElementById("homePage").classList.add("hidden");
    document.getElementById("smsPage").classList.remove("hidden");
    document.getElementById("sms_result").innerHTML = "";
}

function showTransactionChecker() {
    document.getElementById("homePage").classList.add("hidden");
    document.getElementById("transactionPage").classList.remove("hidden");
    document.getElementById("result").innerHTML = "";
}

function goHome() {
    document.getElementById("homePage").classList.remove("hidden");
    document.getElementById("smsPage").classList.add("hidden");
    document.getElementById("transactionPage").classList.add("hidden");
}

// ==============================
// 🚨 CHECK SMS FRAUD
// ==============================
async function checkSMS() {
    const text = document.getElementById("sms_text").value.trim();
    const resultDiv = document.getElementById("sms_result");

    if (!text) {
        resultDiv.style.backgroundColor = "#ffb84d";
        resultDiv.innerHTML = "⚠ Please enter an SMS message.";
        return;
    }

    resultDiv.innerHTML = `<div class="loader"></div>`;

    try {
        const response = await fetch(`${BASE_URL}/predict_sms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        if (!response.ok) throw new Error("Server error");

        const data = await response.json();

        let color, message;

        if (data.prediction === "Spam / Fraud") {
            color = "#ff4d4d";
            message = "❗ This SMS is a scam. DO NOT click any links.";
        } else {
            color = "#4CAF50";
            message = "✅ This SMS looks safe.";
        }

        resultDiv.style.backgroundColor = color;
        resultDiv.innerHTML = `
            <strong>${message}</strong><br>
            <strong>Confidence:</strong> ${Number(data.probability).toFixed(2)}
        `;

    } catch (error) {
        resultDiv.style.backgroundColor = "red";
        resultDiv.innerHTML = "❌ Unable to reach server.";
        console.error("SMS fetch error:", error);
    }
}

// ==============================
// 💸 CHECK TRANSACTION FRAUD
// ==============================
window.onload = function () {
    const form = document.getElementById("transactionForm");
    if (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            checkUPI();
        });
    }
};

async function checkUPI() {
    const transaction = {
        user_id: document.getElementById("user_id").value.trim(),
        payee_name: document.getElementById("payee_name").value.trim(),
        payee_vpa: document.getElementById("payee_vpa").value.trim(),
        amount: parseFloat(document.getElementById("amount").value),
        timestamp: document.getElementById("timestamp").value.replace(" ", "T")
    };

    const resultDiv = document.getElementById("result");
    resultDiv.classList.remove("hidden");
    resultDiv.innerHTML = `<div class="loader"></div>`;

    try {
        const response = await fetch(`${BASE_URL}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(transaction)
        });

        if (!response.ok) throw new Error("Server error");

        const data = await response.json();

        let bg = data.risk_score > 0.7 ? "#ff3b3b" :
                 data.risk_score > 0.4 ? "#ffae42" : "#4CAF50";

        resultDiv.style.backgroundColor = bg;
        resultDiv.innerHTML = `
            <h3>🔍 Fraud Analysis Result</h3>

            <div class="meter">
                <div id="risk-fill"></div>
            </div>

            <p><strong>Risk Score:</strong> ${data.risk_score.toFixed(2)}</p>
            <p><strong>Risk Level:</strong> ${data.risk_level}</p>
            <p><strong>Reasons:</strong> ${data.reasons.join(", ")}</p>

            <div class="tips">
                💡 <strong>Tip:</strong> Always verify payee details before sending money.
            </div>
        `;

        setTimeout(() => {
            document.getElementById("risk-fill").style.width = (data.risk_score * 100) + "%";
            document.getElementById("risk-fill").style.backgroundColor = bg;
        }, 200);

    } catch (err) {
        resultDiv.style.backgroundColor = "#ffb84d";
        resultDiv.innerHTML = "⚠ Unable to reach server.";
        console.error("Transaction fetch error:", err);
    }
}

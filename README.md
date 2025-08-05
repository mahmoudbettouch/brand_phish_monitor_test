# 🛡️ brand_phish_monitor

**Real-time phishing domain detection tool** leveraging CertStream and brand monitoring. Alerts when suspicious domains appear that imitate protected brand names.

---

## 🚀 Features

- Live phishing domain monitoring via **CertStream**.
- Brand similarity detection using **fuzzy matching** and entropy.
- **Email alerts** for detected phishing domains.
- Configurable **cooldown period** to avoid spam.
- Lightweight and easy to set up locally.

---

## 📦 Prerequisites

1. **Python 3.8+**
2. Required Python packages:

Install them via:
```bash
pip install -r requirements.txt
```


## 🐍 Running the Tool

### 1. Start the CertStream server:

```bash
./start_certstream.sh
```

It runs on ws://127.0.0.1:8080.

2. Start phishing domain monitoring:

```bash
python3 brand_phish_monitor.py
```
# Retell / ElevenLabs Cost Simulator

A local Streamlit app for simulating and comparing TTS provider costs across Retell AI configurations.

## What it simulates

| Scenario | Description |
|---|---|
| **Retell + ElevenLabs** | Current setup after the Mar 23 pricing update ($0.04/min TTS) |
| **Retell + Alt TTS** | Switch to Cartesia, Fish Audio, OpenAI, or Retell platform voices ($0.015/min) |
| **Direct ElevenLabs + Retell** | Purchase an ElevenLabs plan directly; pay Retell infra only |

## Requirements

- Python 3.9+
- pip

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/retell-cost-simulator.git
cd retell-cost-simulator
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:
- **macOS / Linux:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## Running in IntelliJ IDEA

1. Open the project folder in IntelliJ
2. Go to **File → Project Structure → SDKs** and point it to your Python interpreter (or the venv above)
3. Open the **Terminal** tab (bottom panel) and run:
   ```bash
   streamlit run app.py
   ```
4. IntelliJ will display the localhost URL — click it or open in your browser

> **Tip:** You can also create a Run Configuration:
> - **Run → Edit Configurations → + → Shell Script**
> - Script: `streamlit`
> - Arguments: `run app.py`
> - Working directory: project root

---

## Adjustable parameters

Use the **sidebar** to change:

| Parameter | Default | Description |
|---|---|---|
| Calls per day | 10 | Total inbound/outbound calls across all agents |
| Avg call duration | 5.2 min | Average length per call |
| Active agents | 2 | Number of Retell agents running |
| Monthly growth % | 0% | Expected month-over-month volume increase |

---

## Notes

- Character estimate: **750 chars/min** (based on ~150 words/min average speech rate)
- ElevenLabs direct plan route assumes Retell supports **BYOK (bring your own API key)** — confirm with Retell support before committing to a plan
- Retell infrastructure fee ($0.055/min) applies in **all** scenarios
- Overage pricing on direct ElevenLabs plans varies by tier (see in-app plan reference table)

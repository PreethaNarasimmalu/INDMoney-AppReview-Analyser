# App Review Pulse — INDMoney Edition

Analyse Google Play reviews for any app using Claude AI.

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API key**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. **Run**
   ```bash
   streamlit run app.py
   ```

## Defaults
| Setting | Default | Range |
|---------|---------|-------|
| App ID | `com.indmoney` | Any Google Play app |
| Date window | 8 weeks | 4 – 16 weeks |
| Max reviews | 1 000 | 50 – 5 000 |

Reviews are fetched newest-first and stopped as soon as they fall outside the chosen date window or the count cap is reached — whichever comes first.

# I Like My Women

An LLM comedy benchmark based on the classic improv game "I like my women like I like my coffee."

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with your OpenRouter API key:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

3. Run the app:
```bash
python app.py
```

4. Open http://localhost:5000

## How it works

- Enter a suggestion (e.g., "coffee")
- Multiple LLMs compete to give the funniest completion
- Vote on your favorite
- See stats on which models are winning

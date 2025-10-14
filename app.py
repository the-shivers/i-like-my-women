import os
import json
import sqlite3
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import random

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')

# OpenRouter setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Track ongoing competitions: {suggestion_id: {contestants: [...], completed: {...}, lock: threading.Lock()}}
active_competitions = {}

# Models to compete
MODELS = [
    {"name": "Claude Sonnet 4.5", "model": "anthropic/claude-sonnet-4.5"},
    {"name": "Claude Opus 4.1", "model": "anthropic/claude-opus-4.1"},
    {"name": "Gemini 2.5 Flash", "model": "google/gemini-2.5-flash", "reasoning_max_tokens": 0},
    {"name": "DeepSeek v3", "model": "deepseek/deepseek-chat-v3-0324"},
    {"name": "GPT-5 Chat", "model": "openai/gpt-5-chat", "reasoning_effort": "low"},
    {"name": "GPT-5 Mini", "model": "openai/gpt-5-mini", "reasoning_effort": "low"},
    {"name": "GPT-5 Nano", "model": "openai/gpt-5-nano", "reasoning_effort": "low"},
    {"name": "Qwen3 235B", "model": "qwen/qwen3-235b-a22b-2507"},
    {"name": "Llama 4 Maverick", "model": "meta-llama/llama-4-maverick"},
    {"name": "Kimi K2", "model": "moonshotai/kimi-k2-0905"},
    {"name": "Llama 4 Scout", "model": "meta-llama/llama-4-scout"},
    {"name": "GLM-4.5-Air", "model": "z-ai/glm-4.5-air", "reasoning_disabled": True},
]

ALL_MODEL_NAMES = [m["name"] for m in MODELS]

SYSTEM_PROMPT = """
You are participating in an improv comedy game called "I like my women."
The user will give you a word or phrase to complete the sentence: "I like my women like I like my [their word]..."
Your goal is to be FUNNY. Use wordplay, double meanings, unexpected twists, or absurdist humor. Keep it short and punchy.
Try not to be an annoying moralist. This is just for fun! Your answer should always be funny, first and foremost.
These answers should usually make sense for both the suggestion and women... i.e. coffee and women can both be "hot."
You should usually try to make your answer work for both the suggestion and women. But things don't always have to make sense though, non-sequiturs are also funny.
Don't think too hard or spend too long thinking. Oftentimes less is more, and remember, brevity is the soul of wit!
IMPORTANT: Respond with ONLY the punchline/completion. Do NOT repeat the full sentence and do NOT use punctuation

Examples:
User: "I like my women like I like my coffee..."
You: "hot"

User: "I like my women like I like my coffee..."
You: "black"

User: "I like my women like I like my coffee..."
You: "with a few pumps of cream"

User: "I like my women like I like my coffee..."
You: "ground up and in the freezer"

Just give the punchline. Nothing else.
"""

# Database setup
def init_db():
    conn = sqlite3.connect('comedy.db')
    c = conn.cursor()

    # Suggestions table
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  word TEXT NOT NULL UNIQUE,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Responses table
    c.execute('''CREATE TABLE IF NOT EXISTS responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  suggestion_id INTEGER NOT NULL,
                  model_name TEXT NOT NULL,
                  model_id TEXT NOT NULL,
                  response_text TEXT NOT NULL,
                  response_time REAL,
                  completion_tokens INTEGER,
                  reasoning_tokens INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (suggestion_id) REFERENCES suggestions(id))''')

    # Votes table
    c.execute('''CREATE TABLE IF NOT EXISTS votes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  suggestion_id INTEGER NOT NULL,
                  response_id INTEGER NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (suggestion_id) REFERENCES suggestions(id),
                  FOREIGN KEY (response_id) REFERENCES responses(id))''')

    # Appearances table - track when responses are shown to users
    c.execute('''CREATE TABLE IF NOT EXISTS appearances
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  response_id INTEGER NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (response_id) REFERENCES responses(id))''')

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect('comedy.db')
    conn.row_factory = sqlite3.Row
    return conn

def call_llm(model_config, word):
    """Call a single LLM and return its response"""
    start_time = time.time()

    try:
        prompt = f'I like my women like I like my {word}...'

        params = {
            "model": model_config['model'],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 2000,
            "extra_body": {
                "usage": {"include": True}
            }
        }

        # Add reasoning effort for OpenAI models (GPT-5) - pass it directly as top-level param
        if model_config.get("reasoning_effort"):
            params["reasoning_effort"] = model_config["reasoning_effort"]
        # Add reasoning max_tokens for Gemini models
        elif model_config.get("reasoning_max_tokens") is not None:
            params['extra_body'].update({'reasoning': {'max_tokens': model_config['reasoning_max_tokens']}})
            params['max_tokens'] = model_config['reasoning_max_tokens']
        # Disable reasoning for GLM models
        elif model_config.get("reasoning_disabled"):
            params['extra_body'].update({'reasoning': {'enabled': False}})

        response = client.chat.completions.create(**params)

        end_time = time.time()
        response_time = end_time - start_time

        content = response.choices[0].message.content

        # Extract token usage if available
        usage = getattr(response, 'usage', None)
        completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        reasoning_tokens = getattr(usage, 'reasoning_tokens', 0) if usage else 0

        print(f"DEBUG {model_config['name']}: Time={response_time:.2f}s, Content='{content}', Tokens={completion_tokens}, Reasoning={reasoning_tokens}")

        if content:
            content = content.strip().strip('"').strip("'")

        return {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'response': content,
            'response_time': response_time,
            'completion_tokens': completion_tokens,
            'reasoning_tokens': reasoning_tokens
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"Error calling {model_config['name']}: {e}")
        return {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'response': f"[Error: {str(e)[:100]}]",
            'response_time': response_time,
            'completion_tokens': 0,
            'reasoning_tokens': 0
        }

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/stats')
def stats():
    return send_from_directory('static', 'stats.html')

@app.route('/<suggestion>')
def suggestion_route(suggestion):
    """Route for suggestions like /coffee, /banana - serves the page and triggers API call via JS"""
    # Let Flask handle static files normally
    if '.' in suggestion:
        return app.send_static_file(suggestion)
    return send_from_directory('static', 'index.html')

def call_llm_and_save(model_config, word, suggestion_id, is_contestant):
    """Call LLM and save result to DB, updating active competition status"""
    result = call_llm(model_config, word)

    db = get_db()
    cursor = db.execute(
        'INSERT INTO responses (suggestion_id, model_name, model_id, response_text, response_time, completion_tokens, reasoning_tokens) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (suggestion_id, result['model_name'], result['model_id'], result['response'], result['response_time'], result['completion_tokens'], result['reasoning_tokens'])
    )
    response_id = cursor.lastrowid
    db.commit()
    db.close()

    response_data = {
        'id': response_id,
        'suggestion_id': suggestion_id,
        'model_name': result['model_name'],
        'model_id': result['model_id'],
        'response_text': result['response'],
        'response_time': result['response_time'],
        'completion_tokens': result['completion_tokens'],
        'reasoning_tokens': result['reasoning_tokens']
    }

    # Update active competition tracking
    if suggestion_id in active_competitions:
        comp = active_competitions[suggestion_id]
        with comp['lock']:
            comp['completed'][model_config['name']] = response_data

    return response_data

@app.route('/api/compete', methods=['POST'])
def compete():
    """Get responses from all models for a given word"""
    data = request.json
    word = data.get('word', '').strip().lower()

    if not word:
        return jsonify({'error': 'No word provided'}), 400

    db = get_db()

    # Check if we already have responses for this word
    suggestion = db.execute('SELECT * FROM suggestions WHERE word = ?', (word,)).fetchone()

    if suggestion:
        # Return cached responses
        responses = db.execute(
            'SELECT * FROM responses WHERE suggestion_id = ?',
            (suggestion['id'],)
        ).fetchall()

        all_responses = [dict(r) for r in responses]

        # Randomly sample 4 contestants
        contestant_responses = random.sample(all_responses, min(4, len(all_responses)))
        contestant_ids = [r['id'] for r in contestant_responses]

        # Group duplicates
        grouped = {}
        for r in contestant_responses:
            text = r['response_text']
            if text not in grouped:
                grouped[text] = {
                    'response': text,
                    'models': [],
                    'response_ids': []
                }
            grouped[text]['models'].append(r['model_name'])
            grouped[text]['response_ids'].append(r['id'])

        # Track appearances - record that these responses were shown
        for r in contestant_responses:
            db.execute('INSERT INTO appearances (response_id) VALUES (?)', (r['id'],))
        db.commit()

        result = {
            'word': word,
            'suggestion_id': suggestion['id'],
            'responses': list(grouped.values()),
            'contestant_ids': contestant_ids,
            'cached': True,
            'all_models': ALL_MODEL_NAMES
        }

        db.close()
        return jsonify(result)

    # New word - create suggestion and select 4 random contestants
    cursor = db.execute('INSERT INTO suggestions (word) VALUES (?)', (word,))
    suggestion_id = cursor.lastrowid
    db.commit()
    db.close()

    # Randomly select 4 contestants
    contestants = random.sample(MODELS, min(4, len(MODELS)))
    contestant_names = [m['name'] for m in contestants]

    # Initialize active competition tracking
    active_competitions[suggestion_id] = {
        'contestants': contestant_names,
        'completed': {},
        'contestant_responses': [],
        'lock': threading.Lock(),
        'ready': False
    }

    def run_models_async():
        """Run all models in background and update when contestants are done"""
        with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
            futures = []
            for model in MODELS:
                is_contestant = model['name'] in contestant_names
                future = executor.submit(call_llm_and_save, model, word, suggestion_id, is_contestant)
                futures.append((model['name'], future, is_contestant))

            # Wait only for contestants to complete
            contestant_responses = []
            for name, future, is_contestant in futures:
                if is_contestant:
                    contestant_responses.append(future.result())

            # Mark as ready and store contestant responses
            comp = active_competitions[suggestion_id]
            with comp['lock']:
                comp['contestant_responses'] = contestant_responses
                comp['ready'] = True

                # Track appearances for contestants
                db = get_db()
                for r in contestant_responses:
                    db.execute('INSERT INTO appearances (response_id) VALUES (?)', (r['id'],))
                db.commit()
                db.close()

    # Start models in background thread
    threading.Thread(target=run_models_async, daemon=True).start()

    return jsonify({
        'word': word,
        'suggestion_id': suggestion_id,
        'cached': False,
        'ready': False,
        'all_models': ALL_MODEL_NAMES
    })

@app.route('/api/compete/status', methods=['GET'])
def compete_status():
    """Check status of ongoing competition and get responses when ready"""
    suggestion_id = request.args.get('suggestion_id', type=int)

    if not suggestion_id or suggestion_id not in active_competitions:
        return jsonify({'error': 'Invalid or completed competition'}), 404

    comp = active_competitions[suggestion_id]
    with comp['lock']:
        completed_count = len([name for name in comp['contestants'] if name in comp['completed']])
        total_count = len(comp['contestants'])
        ready = comp['ready']
        contestant_responses = comp['contestant_responses'] if ready else []

    response_data = {
        'completed': completed_count,
        'total': total_count,
        'ready': ready,
        'all_models': ALL_MODEL_NAMES,
        'contestant_models': comp['contestants']
    }

    if ready:
        # Group duplicates
        grouped = {}
        for r in contestant_responses:
            text = r['response_text']
            if text not in grouped:
                grouped[text] = {
                    'response': text,
                    'models': [],
                    'response_ids': [],
                    'response_time': r['response_time'],
                    'completion_tokens': r['completion_tokens'],
                    'reasoning_tokens': r['reasoning_tokens']
                }
            else:
                # If grouped, take the average timing
                grouped[text]['response_time'] = (grouped[text]['response_time'] + r['response_time']) / 2
                grouped[text]['completion_tokens'] = (grouped[text]['completion_tokens'] + r['completion_tokens']) / 2
                grouped[text]['reasoning_tokens'] = (grouped[text]['reasoning_tokens'] + r['reasoning_tokens']) / 2
            grouped[text]['models'].append(r['model_name'])
            grouped[text]['response_ids'].append(r['id'])

        response_data['responses'] = list(grouped.values())
        response_data['contestant_ids'] = [r['id'] for r in contestant_responses]

    return jsonify(response_data)

@app.route('/api/responses', methods=['GET'])
def get_responses():
    """Get all responses for a suggestion, including incomplete ones"""
    suggestion_id = request.args.get('suggestion_id', type=int)

    if not suggestion_id:
        return jsonify({'error': 'Missing suggestion_id'}), 400

    db = get_db()
    responses = db.execute(
        'SELECT * FROM responses WHERE suggestion_id = ?',
        (suggestion_id,)
    ).fetchall()
    db.close()

    all_responses = [dict(r) for r in responses]

    return jsonify({
        'responses': all_responses,
        'complete': len(all_responses) >= len(MODELS)
    })

@app.route('/api/vote', methods=['POST'])
def vote():
    """Record a vote for a response"""
    data = request.json
    suggestion_id = data.get('suggestion_id')
    response_ids = data.get('response_ids')  # Can be multiple if grouped

    if not suggestion_id or not response_ids:
        return jsonify({'error': 'Missing data'}), 400

    db = get_db()

    # Record vote for each response (if grouped duplicates)
    for response_id in response_ids:
        db.execute(
            'INSERT INTO votes (suggestion_id, response_id) VALUES (?, ?)',
            (suggestion_id, response_id)
        )

    db.commit()
    db.close()

    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get leaderboard stats"""
    db = get_db()

    # Get vote counts and appearance counts per model
    stats = db.execute('''
        SELECT
            r.model_name,
            r.model_id,
            COUNT(DISTINCT v.id) as vote_count,
            COUNT(DISTINCT a.id) as appearance_count
        FROM responses r
        LEFT JOIN votes v ON r.id = v.response_id
        LEFT JOIN appearances a ON r.id = a.response_id
        GROUP BY r.model_name, r.model_id
        ORDER BY vote_count DESC
    ''').fetchall()

    result = [dict(s) for s in stats]
    db.close()

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

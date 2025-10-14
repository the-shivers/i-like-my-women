import os
import json
import sqlite3
import time
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

# Models to compete
MODELS = [
    {"name": "GPT-4", "model": "openai/gpt-4"},
    {"name": "Claude Sonnet", "model": "anthropic/claude-sonnet-4"},
    {"name": "Gemini Pro", "model": "google/gemini-pro"},
    {"name": "Llama 3", "model": "meta-llama/llama-3-70b-instruct"},
]

SYSTEM_PROMPT = """You are participating in an improv comedy game called "I like my women."

The user will give you a word or phrase. You must complete the sentence: "I like my women like I like my [their word]..."

Your goal is to be FUNNY. Use wordplay, double meanings, unexpected twists, or absurdist humor. Keep it short and punchy - one sentence max.

Examples:
- "I like my women like I like my coffee... hot!"
- "I like my women like I like my coffee... black!"
- "I like my women like I like my coffee... with a few pumps of cream"
- "I like my women like I like my coffee... ground up and in the freezer" (dark humor)

Be creative, be funny, be surprising. Just respond with ONLY the completion - nothing else."""

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

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect('comedy.db')
    conn.row_factory = sqlite3.Row
    return conn

def call_llm(model_config, word):
    """Call a single LLM and return its response"""
    try:
        prompt = f'I like my women like I like my {word}...'

        response = client.chat.completions.create(
            model=model_config['model'],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )

        return {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'response': response.choices[0].message.content.strip()
        }
    except Exception as e:
        print(f"Error calling {model_config['name']}: {e}")
        return {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'response': f"[Error: {str(e)}]"
        }

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/stats')
def stats():
    return send_from_directory('static', 'stats.html')

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

        # Randomly sample 4 responses
        if len(all_responses) > 4:
            sampled = random.sample(all_responses, 4)
        else:
            sampled = all_responses

        # Group duplicates
        grouped = {}
        for r in sampled:
            text = r['response_text']
            if text not in grouped:
                grouped[text] = {
                    'response': text,
                    'models': [],
                    'response_ids': []
                }
            grouped[text]['models'].append(r['model_name'])
            grouped[text]['response_ids'].append(r['id'])

        result = {
            'word': word,
            'suggestion_id': suggestion['id'],
            'responses': list(grouped.values()),
            'all_responses': all_responses,
            'cached': True
        }

        db.close()
        return jsonify(result)

    # New word - call all models
    cursor = db.execute('INSERT INTO suggestions (word) VALUES (?)', (word,))
    suggestion_id = cursor.lastrowid
    db.commit()

    # Call all models in parallel
    with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
        results = list(executor.map(lambda m: call_llm(m, word), MODELS))

    # Save responses
    all_responses = []
    for result in results:
        cursor = db.execute(
            'INSERT INTO responses (suggestion_id, model_name, model_id, response_text) VALUES (?, ?, ?, ?)',
            (suggestion_id, result['model_name'], result['model_id'], result['response'])
        )
        response_id = cursor.lastrowid
        all_responses.append({
            'id': response_id,
            'suggestion_id': suggestion_id,
            'model_name': result['model_name'],
            'model_id': result['model_id'],
            'response_text': result['response']
        })

    db.commit()
    db.close()

    # Sample 4 responses
    if len(all_responses) > 4:
        sampled = random.sample(all_responses, 4)
    else:
        sampled = all_responses

    # Group duplicates
    grouped = {}
    for r in sampled:
        text = r['response_text']
        if text not in grouped:
            grouped[text] = {
                'response': text,
                'models': [],
                'response_ids': []
            }
        grouped[text]['models'].append(r['model_name'])
        grouped[text]['response_ids'].append(r['id'])

    return jsonify({
        'word': word,
        'suggestion_id': suggestion_id,
        'responses': list(grouped.values()),
        'all_responses': all_responses,
        'cached': False
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

    # Get vote counts per model
    stats = db.execute('''
        SELECT
            r.model_name,
            r.model_id,
            COUNT(v.id) as vote_count,
            COUNT(DISTINCT r.id) as response_count
        FROM responses r
        LEFT JOIN votes v ON r.id = v.response_id
        GROUP BY r.model_name, r.model_id
        ORDER BY vote_count DESC
    ''').fetchall()

    result = [dict(s) for s in stats]
    db.close()

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

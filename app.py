import os
import sqlite3
import time
import threading
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory, session, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import random

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 2592000  # 30 days

# Rate limiting exemption function
def rate_limit_exempt():
    """Exempt from rate limiting if: debug mode, localhost, or secret header matches"""
    # Exempt in debug mode
    if app.debug:
        return True

    # Exempt localhost
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    if ip in ['127.0.0.1', 'localhost', '::1']:
        return True

    # Exempt if secret header matches
    bypass_secret = os.getenv('RATE_LIMIT_BYPASS_SECRET')
    if bypass_secret:
        header_secret = request.headers.get('X-Bypass-Secret')
        if header_secret == bypass_secret:
            return True

    return False

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
    enabled=lambda: not rate_limit_exempt()
)

# OpenRouter setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Models to compete - Avg response times from benchmark (models >4s are commented out)
MODELS = [
    {"name": "Gemini 2.5 Flash", "model": "google/gemini-2.5-flash", "reasoning_max_tokens": 0},  # 0.69s avg
    {"name": "Llama 4 Scout", "model": "meta-llama/llama-4-scout"},  # 0.75s avg
    # {"name": "Llama 4 Maverick", "model": "meta-llama/llama-4-maverick"},  # 0.78s avg
    {"name": "GPT-4.1", "model": "openai/gpt-4.1"},  # 1.07s avg
    {"name": "Qwen3 235B", "model": "qwen/qwen3-235b-a22b-2507"},  # 1.13s avg
    {"name": "GPT-4o", "model": "openai/gpt-4o", "reasoning_effort": "low"},  # 1.24s avg
    {"name": "DeepSeek Chat v3.1", "model": "deepseek/deepseek-chat-v3.1"},  # 1.48s avg
    # {"name": "Qwen 2.5 72B", "model": "qwen/qwen-2.5-72b-instruct"},  # 1.50s avg
    {"name": "GPT-5 Chat", "model": "openai/gpt-5-chat", "reasoning_effort": "low"},  # 1.53s avg
    # {"name": "Rocinante 12B", "model": "thedrummer/rocinante-12b"},  # 1.72s avg
    {"name": "Claude Sonnet 4.5", "model": "anthropic/claude-sonnet-4.5"},  # 1.83s avg
    {"name": "Claude Haiku 4.5", "model": "anthropic/claude-haiku-4.5"},
    {"name": "Kimi K2", "model": "moonshotai/kimi-k2-0905"},  # 2.19s avg
    # {"name": "Qwen 2.5 VL 32B", "model": "qwen/qwen2.5-vl-32b-instruct"},  # 2.21s avg (too similar to 72B/235B, parking it)
    # {"name": "Claude Opus 4.1", "model": "anthropic/claude-opus-4.1"},  # 2.35s avg (too expensive)
    {"name": "DeepSeek v3", "model": "deepseek/deepseek-chat-v3-0324"},  # 2.49s avg (superseded by v3.1, keeping the newer one)
    # {"name": "DeepSeek Chat v3.0324", "model": "deepseek/deepseek-chat-v3-0324"},  # 3.03s avg (nearly identical to v3.1, set aside)

    # SLOW MODELS (>4s avg) - Commented out for production
    # {"name": "GLM-4.5-Air", "model": "z-ai/glm-4.5-air"},  # 5.13s avg (also uses 333 tokens avg!)
    # {"name": "GPT-5 Mini", "model": "openai/gpt-5-mini", "reasoning_effort": "low"},  # 6.10s avg
    # {"name": "Grok Code Fast 1", "model": "x-ai/grok-code-fast-1"},  # 8.31s avg (915 tokens!)
    # {"name": "Grok 4 Fast", "model": "x-ai/grok-4-fast"},  # 8.86s avg (382 tokens)
    # {"name": "DeepSeek R1T2 Chimera", "model": "tngtech/deepseek-r1t2-chimera"},  # 12.69s avg
    # {"name": "DeepSeek R1 Qwen3 8B", "model": "deepseek/deepseek-r1-0528-qwen3-8b"},  # 15.43s avg
    # {"name": "GPT-5 Nano", "model": "openai/gpt-5-nano", "reasoning_effort": "low"},  # 16.13s avg
    # {"name": "DeepSeek R1", "model": "deepseek/deepseek-r1-0528"},  # 42.04s avg (way too slow!)
]

ALL_MODEL_NAMES = [m["name"] for m in MODELS]

# Random word suggestions - curated list of 200+ funny/interesting nouns
RANDOM_WORDS = [
    # Food & Drinks
    "coffee", "pizza", "tacos", "wine", "beer", "whiskey",
    "pasta", "sandwiches", "soup", "cereal", "tea",

    # Animals
    "cats", "dogs", "horses", "bears", "elephants", "dolphins", "sharks", "hippos",
    "owls", "snakes", "rabbits", "guinea pigs", "ferrets", "monkeys", "pandas",

    # Objects
    "books", "phones", "cameras", "backpacks", "umbrellas", 
    "candles", "lamps", "mirrors", "hammers", "screwdrivers",

    # Nature & Weather
    "storms", "hurricanes", "earthquakes", "volcanoes", "sunshine", "rain", "wind", 
    "mountains", "valleys", "forests", "deserts", "waterfalls",

    # Music & Instruments
    "drums", "cymbals", "tambourines", "harmonicas", "saxophones",
    "microphones", "speakers", "headphones", "vinyl records",

    # Household Items
    "toasters", "coffee makers", "vacuums", "beds", "tables",
    "pillows", "blankets", "towels", "soap", "toothbrushes",

    # Random Fun Stuff
    "fireworks", "balloons", "confetti", "glitter", "magnets", "puzzles", "dice", "playing cards",
    "rubik's cubes", "bouncy balls", "slinkies", "lava lamps", "disco balls", "kazoos", "whoopee cushions", "fidget spinners",

    # Abstract/Funny
    "luck", "secrets", "quests", "myths", "dreams", "nightmares",

    # Famous Figures and Events
    "White Houses", "Donald Trump", "Xi Jinping", "Adolf Hitler", "Taylor Swift", "Elon Musk",
    "MrBeast", "Twitch streamers", "9/11", "Titanic", "Tiananmen Square", "Obama", "Joe Biden",

    # Dark Comedy, other shit I just wanted to add.
    "abortions", "plastic surgeries", "cops", "politicians", "lawyers", "psychologists",
    "dieticians", "Twitter", "AI Labs", "TikToks", "twin towers", "political corruption",
    "slop", "AI-generated slop", "data centers", "mental illnesses", "personality disorders",
    "Discord", "beaches", "boating accidents", "anime", "veal", "factory farming"
]

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

# Database configuration - use Railway volume path if set, otherwise local file
DB_PATH = os.getenv('DATABASE_PATH', 'comedy.db')

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Suggestions table
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  word TEXT NOT NULL UNIQUE,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Responses table - with status and nullable fields for optimistic creation
    c.execute('''CREATE TABLE IF NOT EXISTS responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  suggestion_id INTEGER NOT NULL,
                  model_name TEXT NOT NULL,
                  model_id TEXT NOT NULL,
                  status TEXT DEFAULT 'pending',
                  response_text TEXT,
                  response_time REAL,
                  completion_tokens INTEGER,
                  reasoning_tokens INTEGER,
                  prompt_tokens INTEGER,
                  cost_usd REAL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (suggestion_id) REFERENCES suggestions(id))''')

    # Games table - each row represents one page load/matchup
    c.execute('''CREATE TABLE IF NOT EXISTS games
                 (id TEXT PRIMARY KEY,
                  suggestion_id INTEGER NOT NULL,
                  winning_response_id INTEGER,
                  voter_ip TEXT,
                  voter_session TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (suggestion_id) REFERENCES suggestions(id),
                  FOREIGN KEY (winning_response_id) REFERENCES responses(id))''')

    # Game contestants - which responses were contestants in each game
    c.execute('''CREATE TABLE IF NOT EXISTS game_contestants
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  game_id TEXT NOT NULL,
                  response_id INTEGER NOT NULL,
                  display_position INTEGER,
                  FOREIGN KEY (game_id) REFERENCES games(id),
                  FOREIGN KEY (response_id) REFERENCES responses(id))''')

    # Old tables (kept for backward compatibility)
    c.execute('''CREATE TABLE IF NOT EXISTS votes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  suggestion_id INTEGER NOT NULL,
                  response_id INTEGER NOT NULL,
                  matchup_id TEXT,
                  voter_ip TEXT,
                  voter_session TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (suggestion_id) REFERENCES suggestions(id),
                  FOREIGN KEY (response_id) REFERENCES responses(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS appearances
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  response_id INTEGER NOT NULL,
                  suggestion_id INTEGER NOT NULL,
                  matchup_id TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (response_id) REFERENCES responses(id),
                  FOREIGN KEY (suggestion_id) REFERENCES suggestions(id))''')

    # Migration: Add status column to responses if it doesn't exist
    try:
        c.execute('SELECT status FROM responses LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE responses ADD COLUMN status TEXT DEFAULT "completed"')
        conn.commit()

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')
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
        # Disable reasoning for GLM models - COMMENTED OUT, letting it use reasoning
        # elif model_config.get("reasoning_disabled"):
        #     params['extra_body'].update({'reasoning': {'enabled': False}})

        response = client.chat.completions.create(**params)

        end_time = time.time()
        response_time = end_time - start_time

        content = response.choices[0].message.content

        # Extract token usage and cost if available
        usage = getattr(response, 'usage', None)
        completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        reasoning_tokens = getattr(usage, 'reasoning_tokens', 0) if usage else 0
        prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0

        # OpenRouter returns cost in usage.cost
        # For BYOK (bring your own key) models, cost is 0 but upstream_inference_cost has the actual cost
        cost_usd = 0.0
        if usage and hasattr(usage, 'cost'):
            cost_usd = usage.cost
            # If cost is 0 and we have cost_details, use upstream_inference_cost
            if cost_usd == 0 and hasattr(usage, 'cost_details') and usage.cost_details:
                cost_usd = usage.cost_details.get('upstream_inference_cost', 0.0)

        if content:
            content = content.strip().strip('"').strip("'")

        return {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'response': content,
            'response_time': response_time,
            'completion_tokens': completion_tokens,
            'reasoning_tokens': reasoning_tokens,
            'prompt_tokens': prompt_tokens,
            'cost_usd': cost_usd
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'response': f"[Error: {str(e)[:100]}]",
            'response_time': response_time,
            'completion_tokens': 0,
            'reasoning_tokens': 0,
            'prompt_tokens': 0,
            'cost_usd': 0.0
        }

@app.route('/')
def index():
    # Pick a random word for the homepage
    initial_word = random.choice(RANDOM_WORDS)
    return render_template('index.html', initial_word=initial_word, random_words_json=json.dumps(RANDOM_WORDS))

@app.route('/stats')
def stats():
    return send_from_directory('static', 'stats.html')

@app.route('/loading')
def loading():
    """Test page to view the loading spinner"""
    initial_word = random.choice(RANDOM_WORDS)
    return render_template('index.html', initial_word=initial_word, show_loading=True, random_words_json=json.dumps(RANDOM_WORDS))

@app.route('/random')
def random_word():
    """Redirect to a random word from the list"""
    from flask import redirect
    word = random.choice(RANDOM_WORDS)
    return redirect(f'/{word}')

@app.route('/<suggestion>')
def suggestion_route(suggestion):
    """Route for suggestions like /coffee, /banana - serves the page with word pre-filled"""
    # Let Flask handle static files normally
    if '.' in suggestion:
        return app.send_static_file(suggestion)
    # Render template with the suggestion word
    return render_template('index.html', initial_word=suggestion, random_words_json=json.dumps(RANDOM_WORDS))

def call_llm_and_save(model_config, word, response_id):
    """Call LLM and update response record in DB"""
    result = call_llm(model_config, word)

    db = get_db()
    db.execute(
        '''UPDATE responses
           SET status = 'completed',
               response_text = ?,
               response_time = ?,
               completion_tokens = ?,
               reasoning_tokens = ?,
               prompt_tokens = ?,
               cost_usd = ?
           WHERE id = ?''',
        (result['response'], result['response_time'], result['completion_tokens'],
         result['reasoning_tokens'], result['prompt_tokens'], result['cost_usd'], response_id)
    )
    db.commit()
    db.close()

    response_data = {
        'id': response_id,
        'model_name': result['model_name'],
        'model_id': result['model_id'],
        'response_text': result['response'],
        'response_time': result['response_time'],
        'completion_tokens': result['completion_tokens'],
        'reasoning_tokens': result['reasoning_tokens'],
        'prompt_tokens': result['prompt_tokens'],
        'cost_usd': result['cost_usd'],
        'status': 'completed'
    }

    return response_data

@app.route('/api/compete', methods=['POST'])
@limiter.limit("10/minute")
def compete():
    """Get responses from all models for a given word"""
    data = request.json
    word = data.get('word', '').strip().lower()

    if not word:
        return jsonify({'error': 'No word provided'}), 400

    # Server-side validation: enforce max word length
    if len(word) > 100:
        return jsonify({'error': 'Word too long (max 100 characters)'}), 400

    db = get_db()

    # Check if we already have responses for this word
    suggestion = db.execute('SELECT * FROM suggestions WHERE word = ?', (word,)).fetchone()

    if suggestion:
        # CACHED WORD - create game from existing responses
        responses = db.execute(
            'SELECT * FROM responses WHERE suggestion_id = ? AND status = "completed"',
            (suggestion['id'],)
        ).fetchall()

        all_responses = [dict(r) for r in responses]

        # Randomly sample 4 contestants
        contestant_responses = random.sample(all_responses, min(4, len(all_responses)))
        contestant_ids = [r['id'] for r in contestant_responses]

        # Create game record
        game_id = str(uuid.uuid4())
        db.execute(
            'INSERT INTO games (id, suggestion_id) VALUES (?, ?)',
            (game_id, suggestion['id'])
        )

        # Create game_contestants records
        for position, contestant in enumerate(contestant_responses):
            db.execute(
                'INSERT INTO game_contestants (game_id, response_id, display_position) VALUES (?, ?, ?)',
                (game_id, contestant['id'], position)
            )

        db.commit()

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
                    'reasoning_tokens': r['reasoning_tokens'],
                    'is_contestant': True
                }
            else:
                # If grouped, take the average timing
                grouped[text]['response_time'] = (grouped[text]['response_time'] + r['response_time']) / 2
                grouped[text]['completion_tokens'] = (grouped[text]['completion_tokens'] + r['completion_tokens']) / 2
                grouped[text]['reasoning_tokens'] = (grouped[text]['reasoning_tokens'] + r['reasoning_tokens']) / 2
            grouped[text]['models'].append(r['model_name'])
            grouped[text]['response_ids'].append(r['id'])

        # Get non-contestant responses
        non_contestant_responses = []
        contestant_id_set = set(contestant_ids)
        for r in all_responses:
            if r['id'] not in contestant_id_set:
                non_contestant_responses.append({
                    'model_name': r['model_name'],
                    'response_text': r['response_text'],
                    'response_time': r['response_time'],
                    'completion_tokens': r['completion_tokens'],
                    'reasoning_tokens': r['reasoning_tokens'],
                    'status': 'completed',
                    'is_contestant': False
                })

        result = {
            'word': word,
            'game_id': game_id,
            'suggestion_id': suggestion['id'],
            'responses': list(grouped.values()),
            'contestant_ids': contestant_ids,
            'other_responses': non_contestant_responses,
            'cached': True,
            'ready': True,
            'all_models': ALL_MODEL_NAMES
        }

        db.close()
        return jsonify(result)

    # NEW WORD - create suggestion, pending responses, and game
    cursor = db.execute('INSERT INTO suggestions (word) VALUES (?)', (word,))
    suggestion_id = cursor.lastrowid
    db.commit()

    # Create 11 pending response records
    response_ids = []
    response_map = {}  # model_name -> response_id
    for model in MODELS:
        cursor = db.execute(
            '''INSERT INTO responses (suggestion_id, model_name, model_id, status)
               VALUES (?, ?, ?, 'pending')''',
            (suggestion_id, model['name'], model['model'])
        )
        response_id = cursor.lastrowid
        response_ids.append(response_id)
        response_map[model['name']] = response_id
    db.commit()

    # Randomly select 4 contestants
    contestants = random.sample(MODELS, min(4, len(MODELS)))
    contestant_ids = [response_map[m['name']] for m in contestants]

    # Create game record
    game_id = str(uuid.uuid4())
    db.execute(
        'INSERT INTO games (id, suggestion_id) VALUES (?, ?)',
        (game_id, suggestion_id)
    )

    # Create game_contestants records
    for position, contestant_id in enumerate(contestant_ids):
        db.execute(
            'INSERT INTO game_contestants (game_id, response_id, display_position) VALUES (?, ?, ?)',
            (game_id, contestant_id, position)
        )

    db.commit()
    db.close()

    # Launch all 11 LLM calls in background
    def run_models_async():
        """Run all models in background"""
        with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
            for model in MODELS:
                response_id = response_map[model['name']]
                executor.submit(call_llm_and_save, model, word, response_id)

    threading.Thread(target=run_models_async, daemon=True).start()

    return jsonify({
        'word': word,
        'game_id': game_id,
        'suggestion_id': suggestion_id,
        'cached': False,
        'ready': False,
        'all_models': ALL_MODEL_NAMES
    })

@app.route('/api/compete/status', methods=['GET'])
def compete_status():
    """Check status of ongoing game and get responses when ready"""
    game_id = request.args.get('game_id')

    if not game_id:
        return jsonify({'error': 'Missing game_id'}), 400

    db = get_db()

    # Check if game exists
    game = db.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
    if not game:
        return jsonify({'error': 'Invalid game'}), 404

    suggestion_id = game['suggestion_id']

    # Get contestant responses
    contestant_responses = db.execute(
        '''SELECT r.* FROM responses r
           JOIN game_contestants gc ON r.id = gc.response_id
           WHERE gc.game_id = ?
           ORDER BY gc.display_position''',
        (game_id,)
    ).fetchall()

    contestant_responses = [dict(r) for r in contestant_responses]
    contestant_ids = [r['id'] for r in contestant_responses]

    # Check if all contestants are completed
    completed_count = sum(1 for r in contestant_responses if r['status'] == 'completed')
    total_count = len(contestant_responses)
    ready = completed_count == total_count

    # Get contestant model names
    contestant_models = [r['model_name'] for r in contestant_responses]

    response_data = {
        'completed': completed_count,
        'total': total_count,
        'ready': ready,
        'all_models': ALL_MODEL_NAMES,
        'contestant_models': contestant_models
    }

    if ready:
        # Group contestant duplicates
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
                    'reasoning_tokens': r['reasoning_tokens'],
                    'is_contestant': True
                }
            else:
                # If grouped, take the average timing
                grouped[text]['response_time'] = (grouped[text]['response_time'] + r['response_time']) / 2
                grouped[text]['completion_tokens'] = (grouped[text]['completion_tokens'] + r['completion_tokens']) / 2
                grouped[text]['reasoning_tokens'] = (grouped[text]['reasoning_tokens'] + r['reasoning_tokens']) / 2
            grouped[text]['models'].append(r['model_name'])
            grouped[text]['response_ids'].append(r['id'])

        response_data['responses'] = list(grouped.values())
        response_data['contestant_ids'] = contestant_ids
        response_data['game_id'] = game_id

        # Get all responses for this suggestion
        all_responses = db.execute(
            'SELECT * FROM responses WHERE suggestion_id = ?',
            (suggestion_id,)
        ).fetchall()

        # Add non-contestant responses
        other_responses = []
        contestant_id_set = set(contestant_ids)
        for r in all_responses:
            if r['id'] not in contestant_id_set:
                other_responses.append({
                    'model_name': r['model_name'],
                    'response_text': r['response_text'],
                    'response_time': r['response_time'],
                    'completion_tokens': r['completion_tokens'],
                    'reasoning_tokens': r['reasoning_tokens'],
                    'status': r['status'],
                    'is_contestant': False
                })

        response_data['other_responses'] = other_responses

    db.close()
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
@limiter.limit("30/minute")
def vote():
    """Record a vote for a response"""
    data = request.json
    game_id = data.get('game_id')
    response_ids = data.get('response_ids')  # Can be multiple if grouped

    if not game_id or not response_ids:
        return jsonify({'error': 'Missing data'}), 400

    # Get voter identity
    voter_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in voter_ip:
        voter_ip = voter_ip.split(',')[0].strip()

    # Generate or retrieve session ID
    if 'voter_id' not in session:
        session['voter_id'] = str(uuid.uuid4())
        session.permanent = True
    voter_session = session['voter_id']

    db = get_db()

    # Update game with winning response (use first response_id if multiple due to grouping)
    winning_response_id = response_ids[0] if isinstance(response_ids, list) else response_ids

    db.execute(
        '''UPDATE games
           SET winning_response_id = ?,
               voter_ip = ?,
               voter_session = ?
           WHERE id = ?''',
        (winning_response_id, voter_ip, voter_session, game_id)
    )

    db.commit()
    db.close()

    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get leaderboard stats"""
    db = get_db()

    # Get win counts and appearance counts per model using games table
    stats = db.execute('''
        WITH response_stats AS (
            SELECT
                model_name,
                model_id,
                COUNT(*) AS response_count,
                AVG(response_time) AS avg_response_time,
                AVG(completion_tokens) AS avg_completion_tokens
            FROM responses
            WHERE status = 'completed'
            GROUP BY model_name, model_id
        ),
        win_stats AS (
            SELECT
                r.model_name,
                r.model_id,
                COUNT(DISTINCT g.id) AS vote_count
            FROM responses r
            LEFT JOIN games g ON r.id = g.winning_response_id
            WHERE g.winning_response_id IS NOT NULL
            GROUP BY r.model_name, r.model_id
        ),
        appearance_stats AS (
            SELECT
                r.model_name,
                r.model_id,
                COUNT(DISTINCT gc.id) AS appearance_count
            FROM responses r
            LEFT JOIN game_contestants gc ON r.id = gc.response_id
            LEFT JOIN games g ON gc.game_id = g.id
            WHERE g.winning_response_id IS NOT NULL
            GROUP BY r.model_name, r.model_id
        )
        SELECT
            rs.model_name,
            rs.model_id,
            COALESCE(ws.vote_count, 0) AS vote_count,
            COALESCE(ap.appearance_count, 0) AS appearance_count,
            rs.avg_response_time,
            rs.avg_completion_tokens
        FROM response_stats rs
        LEFT JOIN win_stats ws
            ON rs.model_name = ws.model_name AND rs.model_id = ws.model_id
        LEFT JOIN appearance_stats ap
            ON rs.model_name = ap.model_name AND rs.model_id = ap.model_id
    ''').fetchall()

    result = [dict(s) for s in stats]
    db.close()

    return jsonify(result)

@app.route('/api/costs', methods=['GET'])
def get_costs():
    """Get cost statistics"""
    db = get_db()

    # Total cost
    total_cost = db.execute('SELECT SUM(cost_usd) as total FROM responses').fetchone()

    # Cost by model
    cost_by_model = db.execute('''
        SELECT
            model_name,
            COUNT(*) as request_count,
            SUM(cost_usd) as total_cost,
            AVG(cost_usd) as avg_cost,
            SUM(prompt_tokens) as total_prompt_tokens,
            SUM(completion_tokens) as total_completion_tokens
        FROM responses
        GROUP BY model_name
        ORDER BY total_cost DESC
    ''').fetchall()

    # Cost over time (by day)
    cost_by_day = db.execute('''
        SELECT
            DATE(created_at) as date,
            COUNT(*) as request_count,
            SUM(cost_usd) as total_cost
        FROM responses
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    ''').fetchall()

    db.close()

    return jsonify({
        'total_cost_usd': total_cost['total'] or 0.0,
        'remaining_budget': 100.0 - (total_cost['total'] or 0.0),
        'cost_by_model': [dict(row) for row in cost_by_model],
        'cost_by_day': [dict(row) for row in cost_by_day]
    })

if __name__ == '__main__':
    # Use environment variable for debug mode, default to False for production
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(debug=debug_mode, port=port, host=host)

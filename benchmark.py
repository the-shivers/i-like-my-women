import os
import json
import time
import threading
from openai import OpenAI
from dotenv import load_dotenv
from statistics import mean, stdev
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

load_dotenv()

# OpenRouter setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Models to benchmark
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
    {"name": "GLM-4.5-Air", "model": "z-ai/glm-4.5-air"},
    # New models
    {"name": "GPT-4.1", "model": "openai/gpt-4.1"},  # non-reasoning model
    {"name": "Grok Code Fast 1", "model": "x-ai/grok-code-fast-1"},  # forces reasoning
    {"name": "Grok 4 Fast", "model": "x-ai/grok-4-fast"},  # forces reasoning
    {"name": "GPT-4o", "model": "openai/gpt-4o", "reasoning_effort": "low"},
    {"name": "Qwen 2.5 VL 32B", "model": "qwen/qwen2.5-vl-32b-instruct"},
    {"name": "DeepSeek R1 Qwen3 8B", "model": "deepseek/deepseek-r1-0528-qwen3-8b"},
    {"name": "Qwen 2.5 72B", "model": "qwen/qwen-2.5-72b-instruct"},
    {"name": "Rocinante 12B", "model": "thedrummer/rocinante-12b"},
    {"name": "DeepSeek Chat v3.0324", "model": "deepseek/deepseek-chat-v3-0324"},
    {"name": "DeepSeek R1T2 Chimera", "model": "tngtech/deepseek-r1t2-chimera"},
    {"name": "DeepSeek Chat v3.1", "model": "deepseek/deepseek-chat-v3.1"},
    {"name": "DeepSeek R1", "model": "deepseek/deepseek-r1-0528"},
]

# Test nouns
TEST_NOUNS = [
    "coffee",
    "pizza",
    "cars",
    "cats",
    "wine",
    "hippo",
    "snare drum",
    "storms",
    "books",
    "ice cream"
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

def call_llm(model_config, word):
    """Call a single LLM and return metrics"""
    start_time = time.time()
    timestamp = datetime.now().strftime("%H:%M:%S")

    try:
        prompt = f'I like my women like I like my {word}...'
        print(f"[{timestamp}] [{model_config['name']}] Testing '{word}'...")

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

        # Add reasoning effort for OpenAI models (GPT-5)
        if model_config.get("reasoning_effort"):
            params["reasoning_effort"] = model_config["reasoning_effort"]
        # Add reasoning max_tokens for Gemini models
        elif model_config.get("reasoning_max_tokens") is not None:
            params['extra_body'].update({'reasoning': {'max_tokens': model_config['reasoning_max_tokens']}})
            params['max_tokens'] = model_config['reasoning_max_tokens']

        response = client.chat.completions.create(**params)

        end_time = time.time()
        response_time = end_time - start_time

        content = response.choices[0].message.content
        if content:
            content = content.strip().strip('"').strip("'")

        # Extract token usage
        usage = getattr(response, 'usage', None)
        completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        reasoning_tokens = getattr(usage, 'reasoning_tokens', 0) if usage else 0

        print(f"[{model_config['name']}] → \"{content}\" ({response_time:.2f}s)")

        return {
            'success': True,
            'response': content,
            'response_time': response_time,
            'completion_tokens': completion_tokens,
            'reasoning_tokens': reasoning_tokens,
            'error': None
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"[{model_config['name']}] ERROR: {str(e)[:100]} ({response_time:.2f}s)")
        return {
            'success': False,
            'response': None,
            'response_time': response_time,
            'completion_tokens': 0,
            'reasoning_tokens': 0,
            'error': str(e)[:200]
        }

def benchmark_model(model_config, existing_results=None):
    """Benchmark a single model across all test nouns"""
    # Check if this model already has complete results
    if existing_results and model_config['name'] in existing_results:
        existing = existing_results[model_config['name']]
        if existing.get('total_tests') == len(TEST_NOUNS) and existing.get('successful_tests') == len(TEST_NOUNS):
            print(f"[{model_config['name']}] SKIPPED - already complete in benchmark_results.json")
            return existing

    results = []

    for noun in TEST_NOUNS:
        result = call_llm(model_config, noun)
        results.append(result)

    # Calculate stats
    successful_results = [r for r in results if r['success']]
    success_rate = len(successful_results) / len(results) * 100

    if successful_results:
        response_times = [r['response_time'] for r in successful_results]
        completion_tokens = [r['completion_tokens'] for r in successful_results]
        reasoning_tokens = [r['reasoning_tokens'] for r in successful_results]

        stats = {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'success_rate': success_rate,
            'avg_response_time': mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'std_response_time': stdev(response_times) if len(response_times) > 1 else 0,
            'avg_completion_tokens': mean(completion_tokens) if completion_tokens else 0,
            'avg_reasoning_tokens': mean(reasoning_tokens) if reasoning_tokens else 0,
            'total_tests': len(results),
            'successful_tests': len(successful_results),
            'sample_responses': [r['response'] for r in successful_results[:3]],
            'all_results': results
        }
    else:
        stats = {
            'model_name': model_config['name'],
            'model_id': model_config['model'],
            'success_rate': 0,
            'avg_response_time': 0,
            'min_response_time': 0,
            'max_response_time': 0,
            'std_response_time': 0,
            'avg_completion_tokens': 0,
            'avg_reasoning_tokens': 0,
            'total_tests': len(results),
            'successful_tests': 0,
            'sample_responses': [],
            'all_results': results
        }

    print(f"[{model_config['name']}] DONE! {len(successful_results)}/{len(results)} successful")
    return stats

def print_results_table(all_stats):
    """Print formatted results table"""
    print(f"\n\n{'='*120}")
    print("BENCHMARK RESULTS")
    print(f"{'='*120}\n")

    # Sort by avg response time
    sorted_stats = sorted(all_stats, key=lambda x: x['avg_response_time'])

    # Print header
    print(f"{'Model':<25} {'Success':<8} {'Avg Time':<10} {'Min':<8} {'Max':<8} {'Std':<8} {'Comp Tokens':<12} {'Reasoning':<10}")
    print(f"{'-'*25} {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*12} {'-'*10}")

    # Print rows
    for s in sorted_stats:
        print(f"{s['model_name']:<25} "
              f"{s['success_rate']:>6.0f}%  "
              f"{s['avg_response_time']:>8.2f}s  "
              f"{s['min_response_time']:>6.2f}s  "
              f"{s['max_response_time']:>6.2f}s  "
              f"{s['std_response_time']:>6.2f}s  "
              f"{s['avg_completion_tokens']:>10.1f}  "
              f"{s['avg_reasoning_tokens']:>10.1f}")

    print(f"\n{'='*120}\n")

def main():
    print("Starting benchmark...")
    print(f"Testing {len(MODELS)} models against {len(TEST_NOUNS)} nouns IN PARALLEL")
    print(f"Test nouns: {', '.join(TEST_NOUNS)}\n")

    # Load existing results if available
    existing_results = {}
    output_file = 'benchmark_results.json'
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_list = json.load(f)
                # Convert list to dict keyed by model name
                existing_results = {stat['model_name']: stat for stat in existing_list}
                print(f"Loaded {len(existing_results)} existing results from {output_file}\n")
        except:
            print(f"Could not load existing results from {output_file}\n")

    # Run all models in parallel
    with ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
        futures = [executor.submit(benchmark_model, model, existing_results) for model in MODELS]
        all_stats = [future.result() for future in futures]

    # Print results table
    print_results_table(all_stats)

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(all_stats, f, indent=2)

    print(f"Results saved to {output_file}")

if __name__ == '__main__':
    main()

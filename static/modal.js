// Shared About Modal
(function() {
    // Preload parchment background to prevent text showing before background loads
    const parchmentLoaded = new Promise((resolve) => {
        const img = new Image();
        img.onload = () => resolve();
        img.onerror = () => resolve(); // Resolve anyway on error to not block UI
        img.src = 'parch2.webp';
    });

    // Inject modal CSS
    const style = document.createElement('style');
    style.textContent = `
        /* Modal */
        .modal {
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            background-image: url('parch2.webp');
            background-size: 800px auto;
            padding: 40px;
            border: 2px solid rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 90%;
            max-height: 90vh;
            max-height: 90dvh;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        }

        .modal-content h2 {
            font-family: 'Special Elite', monospace;
            font-size: 2em;
            color: #1a1a1a;
            margin-bottom: 20px;
        }

        .modal-content h3 {
            font-family: 'Special Elite', monospace;
            font-size: 1.4em;
            color: #1a1a1a;
            margin-top: 30px;
            margin-bottom: 15px;
        }

        .modal-content p {
            font-family: 'IBM Plex Serif', serif;
            font-size: 1.1em;
            color: #2a1a1a;
            line-height: 1.6;
            margin-bottom: 15px;
        }

        .modal-content ul {
            font-family: 'IBM Plex Serif', serif;
            font-size: 1.05em;
            color: #2a1a1a;
            line-height: 1.6;
            margin-left: 30px;
            margin-bottom: 15px;
        }

        .modal-content li {
            margin-bottom: 8px;
        }

        .close-modal {
            position: absolute;
            top: 15px;
            right: 25px;
            font-size: 2em;
            font-weight: bold;
            color: #1a1a1a;
            cursor: pointer;
            transition: color 0.3s;
        }

        .close-modal:hover {
            color: #666;
        }

        .hidden {
            display: none !important;
        }
    `;
    document.head.appendChild(style);

    // Inject modal HTML
    const modalHTML = `
        <div id="about-modal" class="modal hidden">
            <div class="modal-content">
                <span class="close-modal">&times;</span>
                <h2>About</h2>

                <h3>Where am I? What the <i>hell</i> is going on?</h3>

                <p>Hey. Welcome to the club. The LLMs are doing improv comedy, and they'll need a suggestion from the audience. That's us. Suppose we tell them to use "coffee." They just have to complete the following sentence in a funny way:</p>

                <p><i>"I like my women like I like my coffee…"</i></p>

                <p>One LLM might say, <b>"hot!"</b> Not bad. See, the word accurately describes how one might like both coffee and women!</p>

                <p>Another might say <b>"black!"</b></p>

                <p>Or even <b>"pumped full of cream!"</b></p>

                <p>And after we have four answers from our LLM contestants, you get to pick which one you think is funniest. That's it!</p>

                <h3>Okay, but seriously?</h3>

                <p>Okay fine.</p>

                <p>This is a semi-serious LLM benchmark to evaluate which LLMs are funniest. Since we can't measure "funny" in an objective way, we fall back to human evaluations, and that's where you come in. If we get enough human feedback, we get a pretty good measure of which models are funniest. And this happens to be a great improv game for LLMs. So there's the benchmark: whichever LLM has the funniest answers in this game, most often, based on human feedback (win rate).</p>

                <h3>Which models are competing?</h3>
                <ul>
                    <li><b>Gemini 2.5 Flash</b> - Google's best "fast" model.</li>
                    <li><b>Llama 4 Scout</b> - Meta diversity hire.</li>
                    <li><b>GPT-4.1</b> - OpenAI's iteration on GPT-4</li>
                    <li><b>Qwen3 235B</b> - Chinese model with a large number of parameters</li>
                    <li><b>GPT-4o</b> - OpenAI personality hire.</li>
                    <li><b>DeepSeek Chat v3.1</b> - I know I'm not supposed to pick favorites, but I don't care for this one.</li>
                    <li><b>GPT-5 Chat</b> - Non-thinking (lobotomized) version of GPT-5</li>
                    <li><b>Claude Sonnet 4.5</b> - Anthropic's dearest, darlingest.</li>
                    <li><b>Kimi K2</b> - Moonshot AI's hyped-up model</li>
                    <li><b>DeepSeek v3</b> - Added this because I was mad at how long DeepSeek v3.1's responses were taking but I think it was just a really bad OpenRouter provider.</li>
                </ul>

                <p>Four random "contestant" models are selected each round. If two models give the same answer, they're merged during the selection phase.</p>

                <h3>Why isn't [model] included?</h3>

                <p>Good question.</p>

                <p>The most common reason is speed. This is an improv comedy benchmark, and not a David Sedaris essay-writing benchmark. These models gotta be able to think on their feet! I don't care if they (e.g. Grok 4, Gemini 2.5 Pro) can be funny after they think about it for an hour! That would make for a terrible user experience! But if <i>you</i> wanna make Costanza-bench, go ahead.</p>

                <p>Some were excluded for their high price (Opus 4.1). And some were excluded just because I didn't want to have too many models from a single line of models.

                <h3>Can I see the data?</h3>

                <p>It's right <a href="/stats" style="color: #1a1a1a; text-decoration: underline;">here</a>, babe.</p>
            </div>
        </div>
    `;

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        // Inject modal into body
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Set up event listeners
        const aboutLink = document.getElementById('about-link');
        const modal = document.getElementById('about-modal');
        const closeBtn = modal.querySelector('.close-modal');

        aboutLink.addEventListener('click', async function(e) {
            e.preventDefault();
            await parchmentLoaded;
            modal.classList.remove('hidden');
        });

        closeBtn.addEventListener('click', function() {
            modal.classList.add('hidden');
        });

        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
})();

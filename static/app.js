let currentData = null;

// DOM elements
const inputSection = document.getElementById('input-section');
const loadingSection = document.getElementById('loading-section');
const resultsSection = document.getElementById('results-section');
const revealSection = document.getElementById('reveal-section');
const wordInput = document.getElementById('word-input');
const submitBtn = document.getElementById('submit-btn');
const responsesContainer = document.getElementById('responses-container');
const revealContainer = document.getElementById('reveal-container');
const newRoundBtn = document.getElementById('new-round-btn');

// Show/hide sections
function showSection(section) {
    [inputSection, loadingSection, resultsSection, revealSection].forEach(s => {
        s.classList.add('hidden');
    });
    section.classList.remove('hidden');
}

// Check URL for suggestion on page load
window.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    if (path !== '/' && path !== '/stats') {
        const suggestion = path.substring(1); // Remove leading slash
        wordInput.value = decodeURIComponent(suggestion);
        submitBtn.click();
    }
});

// Submit word
submitBtn.addEventListener('click', async () => {
    const word = wordInput.value.trim();
    if (!word) return;

    // Update URL with suggestion as path
    window.history.pushState({}, '', `/${encodeURIComponent(word)}`);

    showSection(loadingSection);

    try {
        const response = await fetch('/api/compete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word })
        });

        currentData = await response.json();
        currentData.all_models = currentData.all_models || [];

        // If cached, display immediately
        if (currentData.cached) {
            displayResponses();
            return;
        }

        // Otherwise, poll for status
        const pollInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`/api/compete/status?suggestion_id=${currentData.suggestion_id}`);
                const status = await statusResponse.json();

                // Update loading text
                const loadingText = document.querySelector('#loading-section p');
                if (loadingText) {
                    loadingText.textContent = `Loading responses (${status.completed}/${status.total})...`;
                }

                // When ready, stop polling and display
                if (status.ready) {
                    clearInterval(pollInterval);
                    currentData.responses = status.responses;
                    currentData.contestant_ids = status.contestant_ids;
                    if (status.all_models) {
                        currentData.all_models = status.all_models;
                    }
                    displayResponses();
                }
            } catch (error) {
                clearInterval(pollInterval);
                alert('Error: ' + error.message);
                showSection(inputSection);
            }
        }, 500);

    } catch (error) {
        alert('Error: ' + error.message);
        showSection(inputSection);
    }
});

// Allow Enter key to submit
wordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitBtn.click();
    }
});

// Display responses for voting
function displayResponses() {
    responsesContainer.innerHTML = '';

    // Shuffle responses randomly
    const shuffled = [...currentData.responses].sort(() => Math.random() - 0.5);
    currentData.displayOrder = shuffled.map(item => ({
        response: item.response,
        response_ids: [...item.response_ids],
        models: [...item.models]
    }));

    shuffled.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'response-card';

        const timeInfo = item.response_time ? `<div class="time-info-small">${item.response_time.toFixed(2)}s</div>` : '';

        card.innerHTML = `
            <div class="response-number">${index + 1}</div>
            <div class="response-text">"${item.response}"</div>
            ${timeInfo}
        `;
        card.addEventListener('click', () => vote(item, card));
        responsesContainer.appendChild(card);
    });

    showSection(resultsSection);
}

// Vote for a response
async function vote(item, cardElement) {
    // Disable all cards
    document.querySelectorAll('.response-card').forEach(card => {
        card.style.pointerEvents = 'none';
    });

    // Highlight selected
    cardElement.classList.add('selected');

    // Record vote
    try {
        await fetch('/api/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                suggestion_id: currentData.suggestion_id,
                response_ids: item.response_ids
            })
        });

        // Show reveal after short delay
        setTimeout(() => reveal(item), 500);
    } catch (error) {
        alert('Error recording vote: ' + error.message);
    }
}

// Reveal which models gave which answers
function reveal(selectedItem) {
    const header = document.createElement('div');
    header.className = 'reveal-header';
    header.innerHTML = `<h3>I like my women like I like my ${currentData.word}...</h3>`;

    const contestantSection = document.createElement('div');
    contestantSection.id = 'contestant-reveal';

    const otherHeading = document.createElement('h4');
    otherHeading.className = 'reveal-subheading';
    otherHeading.textContent = 'Other answers';

    const otherSection = document.createElement('div');
    otherSection.id = 'other-answers';

    revealContainer.innerHTML = '';
    revealContainer.appendChild(header);
    revealContainer.appendChild(contestantSection);
    revealContainer.appendChild(otherHeading);
    revealContainer.appendChild(otherSection);

    showSection(revealSection);

    // Fetch all responses and poll for incomplete ones
    async function loadAllResponses() {
        try {
            const response = await fetch(`/api/responses?suggestion_id=${currentData.suggestion_id}`);
            const data = await response.json();
            const responsesByModel = new Map();
            data.responses.forEach(r => {
                responsesByModel.set(r.model_name, r);
            });

            renderContestants(responsesByModel);
            renderOtherAnswers(responsesByModel);

            // If not complete, poll again
            if (!data.complete) {
                setTimeout(loadAllResponses, 1000);
            }
        } catch (error) {
            console.error('Error loading responses:', error);
        }
    }

    function renderContestants(responsesByModel) {
        contestantSection.innerHTML = '';
        const order = currentData.displayOrder && currentData.displayOrder.length
            ? currentData.displayOrder
            : currentData.responses;

        order.forEach(item => {
            const isSelected = selectedItem.response_ids.some(id => item.response_ids.includes(id));
            const card = document.createElement('div');
            card.className = `reveal-card ${isSelected ? 'winner' : ''}`;

            const responseText = document.createElement('div');
            responseText.className = 'reveal-response';
            responseText.textContent = `"${item.response}"`;
            card.appendChild(responseText);

            item.models.forEach(modelName => {
                const modelBlock = document.createElement('div');
                modelBlock.className = 'reveal-model-block';
                const modelResponse = responsesByModel.get(modelName);

                if (modelResponse) {
                    const modelNameDiv = document.createElement('div');
                    modelNameDiv.className = 'reveal-model';
                    modelNameDiv.textContent = modelName;
                    modelBlock.appendChild(modelNameDiv);

                    if (typeof modelResponse.response_time === 'number') {
                        const timeInfo = document.createElement('div');
                        timeInfo.className = 'time-info';
                        timeInfo.textContent = `${modelResponse.response_time.toFixed(2)}s`;
                        modelBlock.appendChild(timeInfo);
                    }

                    if (modelResponse.completion_tokens || modelResponse.reasoning_tokens) {
                        const tokensInfo = document.createElement('div');
                        tokensInfo.className = 'token-info';
                        tokensInfo.textContent = `${modelResponse.completion_tokens || 0} tokens${modelResponse.reasoning_tokens ? ` (${modelResponse.reasoning_tokens} reasoning)` : ''}`;
                        modelBlock.appendChild(tokensInfo);
                    }
                } else {
                    modelBlock.innerHTML = `
                        <div class="reveal-model">${modelName}</div>
                        <div class="placeholder-row">
                            <div class="mini-spinner"></div>
                            <span>Waiting for response...</span>
                        </div>
                    `;
                }

                card.appendChild(modelBlock);
            });

            if (isSelected) {
                const badge = document.createElement('div');
                badge.className = 'winner-badge';
                badge.textContent = 'Your Pick!';
                card.appendChild(badge);
            }

            contestantSection.appendChild(card);
        });
    }

    function renderOtherAnswers(responsesByModel) {
        otherSection.innerHTML = '';

        const contestantModels = new Set();
        const order = currentData.displayOrder && currentData.displayOrder.length
            ? currentData.displayOrder
            : currentData.responses;
        order.forEach(item => item.models.forEach(model => contestantModels.add(model)));

        const allModels = (currentData.all_models && currentData.all_models.length)
            ? currentData.all_models
            : Array.from(responsesByModel.keys());

        const otherModels = allModels.filter(model => !contestantModels.has(model));

        if (!otherModels.length) {
            const none = document.createElement('div');
            none.className = 'placeholder-row no-other-answers';
            none.textContent = 'No other answers for this suggestion yet.';
            otherSection.appendChild(none);
            return;
        }

        otherModels.forEach(modelName => {
            const card = document.createElement('div');
            card.className = 'reveal-card';

            const modelResponse = responsesByModel.get(modelName);
            const modelDiv = document.createElement('div');
            modelDiv.className = 'reveal-model';
            modelDiv.textContent = modelName;
            card.appendChild(modelDiv);

            if (modelResponse) {
                const responseText = document.createElement('div');
                responseText.className = 'reveal-response';
                responseText.textContent = `"${modelResponse.response_text}"`;
                card.appendChild(responseText);

                if (typeof modelResponse.response_time === 'number') {
                    const timeInfo = document.createElement('div');
                    timeInfo.className = 'time-info';
                    timeInfo.textContent = `${modelResponse.response_time.toFixed(2)}s`;
                    card.appendChild(timeInfo);
                }

                if (modelResponse.completion_tokens || modelResponse.reasoning_tokens) {
                    const tokensInfo = document.createElement('div');
                    tokensInfo.className = 'token-info';
                    tokensInfo.textContent = `${modelResponse.completion_tokens || 0} tokens${modelResponse.reasoning_tokens ? ` (${modelResponse.reasoning_tokens} reasoning)` : ''}`;
                    card.appendChild(tokensInfo);
                }
            } else {
                const placeholder = document.createElement('div');
                placeholder.className = 'placeholder-row';
                placeholder.innerHTML = `
                    <div class="mini-spinner"></div>
                    <span>Waiting for response...</span>
                `;
                card.appendChild(placeholder);
            }

            otherSection.appendChild(card);
        });
    }

    renderContestants(new Map());
    renderOtherAnswers(new Map());
    loadAllResponses();
}

// Start new round
newRoundBtn.addEventListener('click', () => {
    wordInput.value = '';
    currentData = null;
    // Clear URL params
    window.history.pushState({}, '', '/');
    showSection(inputSection);
    wordInput.focus();
});

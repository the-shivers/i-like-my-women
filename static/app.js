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

    // Clear old data first
    currentData = null;

    // Update URL with suggestion as path
    window.history.pushState({}, '', `/${encodeURIComponent(word)}`);

    // Reset loading text
    const loadingText = document.querySelector('#loading-section p');
    if (loadingText) {
        loadingText.textContent = 'The LLMs are thinking...';
    }

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

    // Create a card for EACH contestant model
    const allContestantCards = [];
    currentData.responses.forEach(item => {
        item.models.forEach((modelName, idx) => {
            allContestantCards.push({
                response: item.response,
                modelName: modelName,
                response_id: item.response_ids[idx]
            });
        });
    });

    // Shuffle all contestant cards randomly
    const shuffled = [...allContestantCards].sort(() => Math.random() - 0.5);
    currentData.displayOrder = shuffled;

    // Track seen responses to hide duplicates during voting
    const seenResponses = new Set();

    shuffled.forEach((item, actualIndex) => {
        const card = document.createElement('div');
        card.className = 'response-card';
        card.dataset.responseId = item.response_id;
        card.dataset.modelName = item.modelName;
        card.dataset.response = item.response; // Store response text for duplicate detection
        card.dataset.actualIndex = actualIndex;

        // Check if this is a duplicate response
        const isDuplicate = seenResponses.has(item.response);
        if (isDuplicate) {
            card.classList.add('duplicate-hidden');
        } else {
            seenResponses.add(item.response);
        }

        card.innerHTML = `
            <div class="response-text">"${item.response}"</div>
            <div class="model-info model-info-placeholder"></div>
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
                response_ids: [item.response_id]
            })
        });

        // Show reveal in-place immediately
        revealInPlace(item.response_id);
    } catch (error) {
        alert('Error recording vote: ' + error.message);
    }
}

// Reveal models in-place - just add model info to each card
function revealInPlace(selectedResponseId) {
    // Change section title
    const resultsTitle = document.querySelector('#results-section h2');
    if (resultsTitle) {
        resultsTitle.textContent = 'Results';
    }

    // Add "Try Another" button if not already there
    if (!document.querySelector('#try-another-inline-btn')) {
        const btnContainer = document.createElement('div');
        btnContainer.style.marginTop = '20px';
        btnContainer.style.textAlign = 'center';
        const tryAnotherBtn = document.createElement('button');
        tryAnotherBtn.id = 'try-another-inline-btn';
        tryAnotherBtn.className = 'btn btn-secondary';
        tryAnotherBtn.textContent = 'Try Another';
        tryAnotherBtn.addEventListener('click', () => {
            wordInput.value = '';
            currentData = null;
            window.history.pushState({}, '', '/');
            showSection(inputSection);
            wordInput.focus();
        });
        btnContainer.appendChild(tryAnotherBtn);
        resultsSection.appendChild(btnContainer);
    }

    // Fetch all responses
    async function loadAllResponses() {
        try {
            const response = await fetch(`/api/responses?suggestion_id=${currentData.suggestion_id}`);
            const data = await response.json();
            const responsesById = new Map();
            data.responses.forEach(r => {
                responsesById.set(r.id, r);
            });

            updateCards(responsesById);

            // If not complete, poll again
            if (!data.complete) {
                setTimeout(loadAllResponses, 1000);
            }
        } catch (error) {
            console.error('Error loading responses:', error);
        }
    }

    function updateCards(responsesById) {
        const cards = responsesContainer.querySelectorAll('.response-card');

        // Find the selected response text to highlight all duplicates
        let selectedResponseText = null;
        cards.forEach((card) => {
            const responseId = parseInt(card.dataset.responseId);
            if (responseId === selectedResponseId) {
                selectedResponseText = card.dataset.response;
            }
        });

        cards.forEach((card) => {
            const responseId = parseInt(card.dataset.responseId);
            const modelName = card.dataset.modelName;
            const responseText = card.dataset.response;
            const modelResponse = responsesById.get(responseId);

            // Show all cards (including previously hidden duplicates)
            card.classList.remove('duplicate-hidden');

            // Check if this should be highlighted (either selected or duplicate of selected)
            const shouldHighlight = selectedResponseText && responseText === selectedResponseText;

            // Update model info (only once, when it's a placeholder)
            const existingInfo = card.querySelector('.model-info');
            if (existingInfo && existingInfo.classList.contains('model-info-placeholder')) {
                existingInfo.classList.remove('model-info-placeholder');
                existingInfo.innerHTML = '';

                if (modelResponse) {
                    const modelNameSpan = document.createElement('span');
                    modelNameSpan.className = 'model-name-inline';
                    modelNameSpan.textContent = modelName;
                    existingInfo.appendChild(modelNameSpan);

                    if (typeof modelResponse.response_time === 'number') {
                        const timeSpan = document.createElement('span');
                        timeSpan.className = 'time-info-inline';
                        timeSpan.textContent = `${modelResponse.response_time.toFixed(2)}s`;
                        existingInfo.appendChild(timeSpan);
                    }

                    if (modelResponse.completion_tokens) {
                        const tokenSpan = document.createElement('span');
                        tokenSpan.className = 'token-info-inline';
                        tokenSpan.textContent = `${modelResponse.completion_tokens} tok`;
                        existingInfo.appendChild(tokenSpan);
                    }
                } else {
                    existingInfo.innerHTML = `<span class="model-name-inline">${modelName}</span><span class="loading-inline">Loading...</span>`;
                }
            }

            // Highlight all cards with matching response text
            if (shouldHighlight) {
                card.classList.add('winner');
            }
        });
    }

    // Start loading immediately (don't call updateCards with empty Map)
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

let currentData = null;
let selectedCard = null;

// DOM elements
const input = document.getElementById('word-input');
const wiggleDisplay = document.getElementById('wiggle-display');
const inputWrapper = document.querySelector('.input-wrapper');
const submitBtn = document.getElementById('submit-btn');
const randomBtn = document.getElementById('random-btn');
const answersContainer = document.getElementById('answers-container');
const loadingContainer = document.getElementById('loading-container');

// Random words list (matches backend)
const randomWords = ['coffee', 'pizza', 'cars', 'wine', 'storms', 'books', 'cats', 'tacos'];

// Set random word on load (unless URL has a suggestion)
const path = window.location.pathname;
if (path !== '/' && path !== '/stats' && path !== '/about') {
    const suggestion = path.substring(1); // Remove leading slash
    input.value = decodeURIComponent(suggestion);
} else {
    input.value = randomWords[Math.floor(Math.random() * randomWords.length)];
}

// Update wiggle display with individual letter spans
function updateWiggleDisplay() {
    const text = input.value || '';
    const displayText = text || ' ';

    wiggleDisplay.innerHTML = displayText.split('').map(char =>
        `<span>${char === ' ' ? '&nbsp;' : char}</span>`
    ).join('');

    // Resize wrapper to fit content (enforce minimum width)
    const tempSpan = document.createElement('span');
    tempSpan.style.font = window.getComputedStyle(wiggleDisplay).font;
    tempSpan.style.visibility = 'hidden';
    tempSpan.style.position = 'absolute';
    tempSpan.textContent = displayText;
    document.body.appendChild(tempSpan);
    inputWrapper.style.width = Math.max(30, tempSpan.offsetWidth + 5) + 'px';
    document.body.removeChild(tempSpan);
}

// Wait for font to load before sizing
document.fonts.ready.then(() => {
    updateWiggleDisplay();

    // Auto-focus and put cursor at end (only if not submitting from URL)
    if (path === '/' || path === '') {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    } else {
        // URL has suggestion, submit it
        submitBtn.click();
    }
});

input.addEventListener('input', updateWiggleDisplay);

// Allow clicking on wiggle display to focus input
wiggleDisplay.addEventListener('click', () => {
    input.focus();
});

// Random button functionality
randomBtn.addEventListener('click', () => {
    input.value = randomWords[Math.floor(Math.random() * randomWords.length)];
    updateWiggleDisplay();
    input.focus();
});

// Generate answer cards with random styling
function generateAnswerCards(responses) {
    answersContainer.innerHTML = '';

    responses.forEach((responseData, index) => {
        const card = document.createElement('div');
        card.className = 'answer-card';
        card.dataset.responseIds = JSON.stringify(responseData.response_ids);
        card.dataset.models = JSON.stringify(responseData.models);

        // Random rotation between -1.5 and 1.5 degrees
        const rotation = (Math.random() * 3 - 1.5).toFixed(1);

        // Random horizontal shift between -15px and 15px
        const translateX = Math.floor(Math.random() * 30 - 15);

        // Random background position
        const bgX = Math.floor(Math.random() * 100);
        const bgY = Math.floor(Math.random() * 100);

        // Alternate slide direction
        const slideDir = index % 2 === 0 ? 'slide-left' : 'slide-right';
        card.classList.add(slideDir);

        // Apply random styling
        card.style.transform = `rotate(${rotation}deg) translateX(${translateX}px)`;
        card.style.backgroundPosition = `${bgX}% ${bgY}%`;

        // Add text (left column, spans both rows)
        const text = document.createElement('div');
        text.className = 'answer-text';
        text.textContent = responseData.response;
        card.appendChild(text);

        // Add model name (top right) - will be revealed on click
        const modelName = document.createElement('div');
        modelName.className = 'model-name';
        modelName.textContent = responseData.models.join(', '); // If multiple models gave same answer
        card.appendChild(modelName);

        // Add model stats (bottom right) - will be revealed on click
        const modelStats = document.createElement('div');
        modelStats.className = 'model-stats';
        const timeStr = responseData.response_time ? `${responseData.response_time.toFixed(2)}s` : '...';
        const tokenStr = responseData.completion_tokens ? `${Math.round(responseData.completion_tokens)} tokens` : '...';
        modelStats.textContent = `${timeStr} • ${tokenStr}`;
        card.appendChild(modelStats);

        // Click handler - reveal model info and record vote
        card.addEventListener('click', () => selectCard(card, responseData));

        answersContainer.appendChild(card);
    });
}

// Submit button - show answers
async function showAnswers() {
    const word = input.value.trim();
    if (!word) return;

    // Update URL
    window.history.pushState({}, '', `/${encodeURIComponent(word)}`);

    // Clear previous results and show loading
    answersContainer.innerHTML = '';
    answersContainer.classList.add('hidden');
    loadingContainer.classList.remove('hidden');
    selectedCard = null;

    try {
        const response = await fetch('/api/compete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word })
        });

        currentData = await response.json();

        // If cached, display immediately
        if (currentData.cached) {
            loadingContainer.classList.add('hidden');
            generateAnswerCards(currentData.responses);
            answersContainer.classList.remove('hidden');
            return;
        }

        // Otherwise, poll for status
        const pollInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`/api/compete/status?suggestion_id=${currentData.suggestion_id}`);
                const status = await statusResponse.json();

                // When ready, stop polling and display
                if (status.ready) {
                    clearInterval(pollInterval);
                    loadingContainer.classList.add('hidden');
                    currentData.responses = status.responses;
                    currentData.contestant_ids = status.contestant_ids;
                    generateAnswerCards(currentData.responses);
                    answersContainer.classList.remove('hidden');
                }
            } catch (error) {
                clearInterval(pollInterval);
                loadingContainer.classList.add('hidden');
                alert('Error: ' + error.message);
            }
        }, 500);

    } catch (error) {
        loadingContainer.classList.add('hidden');
        alert('Error: ' + error.message);
    }
}

// Select a card - reveal info and record vote
async function selectCard(card, responseData) {
    // If already selected a card, don't allow changing
    if (selectedCard) return;

    selectedCard = card;

    // Mark as selected and revealed
    card.classList.add('selected');
    card.classList.add('revealed');

    // Disable all cards
    document.querySelectorAll('.answer-card').forEach(c => {
        c.style.pointerEvents = 'none';
    });

    // Record vote
    try {
        await fetch('/api/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                suggestion_id: currentData.suggestion_id,
                response_ids: responseData.response_ids
            })
        });
    } catch (error) {
        console.error('Error recording vote:', error);
    }
}

submitBtn.addEventListener('click', showAnswers);

// Enter key submits
input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        showAnswers();
    }
});

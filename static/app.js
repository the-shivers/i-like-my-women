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
        displayResponses();
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

    shuffled.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'response-card';
        card.innerHTML = `
            <div class="response-number">${index + 1}</div>
            <div class="response-text">"${item.response}"</div>
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
    revealContainer.innerHTML = `
        <div class="reveal-header">
            <h3>I like my women like I like my ${currentData.word}...</h3>
        </div>
    `;

    // Show all responses with model names and timing
    currentData.all_responses.forEach(r => {
        const isSelected = selectedItem.response_ids.includes(r.id);
        const card = document.createElement('div');
        card.className = `reveal-card ${isSelected ? 'winner' : ''}`;

        const timeInfo = r.response_time ? `<div class="time-info">${r.response_time.toFixed(2)}s</div>` : '';
        const tokenInfo = (r.completion_tokens || r.reasoning_tokens)
            ? `<div class="token-info">${r.completion_tokens || 0} tokens${r.reasoning_tokens ? ` (${r.reasoning_tokens} reasoning)` : ''}</div>`
            : '';

        card.innerHTML = `
            <div class="reveal-model">${r.model_name}</div>
            <div class="reveal-response">"${r.response_text}"</div>
            ${timeInfo}
            ${tokenInfo}
            ${isSelected ? '<div class="winner-badge">Your Pick!</div>' : ''}
        `;
        revealContainer.appendChild(card);
    });

    showSection(revealSection);
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

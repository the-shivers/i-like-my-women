let currentData = null;
let selectedCard = null;
let otherResponses = [];  // Store other (non-contestant) responses

// DOM elements
const input = document.getElementById('word-input');
const wiggleDisplay = document.getElementById('wiggle-display');
const inputWrapper = document.querySelector('.input-wrapper');
const submitBtn = document.getElementById('submit-btn');
const randomBtn = document.getElementById('random-btn');
const answersContainer = document.getElementById('answers-container');
const loadingContainer = document.getElementById('loading-container');
const loadingProgress = document.getElementById('loading-progress');
const actionButtons = document.getElementById('action-buttons');
const showOthersBtn = document.getElementById('show-others-btn');
const resetBtn = document.getElementById('reset-btn');
const otherAnswers = document.getElementById('other-answers');
const otherAnswersContainer = document.getElementById('other-answers-container');
const brickWall = document.querySelector('.brick-wall');
const stage = document.querySelector('.stage');

// Graffiti images (pre-colored cyan) and hue shifts
const graffitiImages = ['p1cyan.webp', 'p2cyan.webp', 'p3cyan.webp'];
const graffitiHueShifts = [
    0,      // cyan (no shift)
    120,    // magenta (cyan + 120deg)
    -120    // yellow (cyan - 120deg)
];

// Function to clear all graffiti
function clearGraffiti() {
    const existingGraffiti = document.querySelectorAll('.graffiti-icon');
    existingGraffiti.forEach(icon => icon.remove());
}

// Graffiti drawing function
function drawGraffiti(clientX, clientY) {
    // Get click position relative to the stage
    const rect = stage.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    // Create graffiti icon
    const icon = document.createElement('img');
    icon.className = 'graffiti-icon';

    // Random image
    const randomImage = graffitiImages[Math.floor(Math.random() * graffitiImages.length)];
    icon.src = randomImage;

    // Random size (between 80px and 200px)
    const size = 80 + Math.random() * 120;
    icon.style.width = size + 'px';
    icon.style.height = 'auto';

    // Random rotation (0 to 360 degrees)
    const rotation = Math.random() * 360;

    // Random flip (horizontal and/or vertical)
    const flipX = Math.random() > 0.5 ? -1 : 1;
    const flipY = Math.random() > 0.5 ? -1 : 1;

    // Random color (hue shift from cyan base)
    const hueShift = graffitiHueShifts[Math.floor(Math.random() * graffitiHueShifts.length)];

    // Position centered on click (accounting for size)
    icon.style.left = (x - size / 2) + 'px';
    icon.style.top = (y - size / 2) + 'px';

    // Apply transform (rotation and flip)
    icon.style.transform = `rotate(${rotation}deg) scale(${flipX}, ${flipY})`;

    // Apply hue shift to get different colors from cyan base
    icon.style.filter = `hue-rotate(${hueShift}deg)`;

    // Add to stage
    stage.appendChild(icon);
}

// Forward clicks on empty content area to brick wall
const content = document.querySelector('.content');
content.addEventListener('click', (e) => {
    // Only forward if clicking directly on content (empty space), not on children
    if (e.target === content) {
        drawGraffiti(e.clientX, e.clientY);
    }
});

// Brick wall click handler - add graffiti
brickWall.addEventListener('click', (e) => {
    drawGraffiti(e.clientX, e.clientY);
});

// Random words list (matches backend)
const randomWords = [
    "coffee", "pizza", "tacos", "wine", "beer", "whiskey", "tequila", "vodka", "champagne",
    "sushi", "burgers", "hot dogs", "ice cream", "donuts", "cookies", "cake", "pie", "steak",
    "pasta", "ramen", "sandwiches", "salad", "soup", "curry", "bbq", "bacon", "eggs",
    "pancakes", "waffles", "cereal", "toast", "bagels", "croissants", "tea", "kombucha",
    "cats", "dogs", "horses", "lions", "tigers", "bears", "elephants", "dolphins", "sharks",
    "eagles", "owls", "penguins", "flamingos", "peacocks", "snakes", "lizards", "turtles",
    "rabbits", "hamsters", "guinea pigs", "ferrets", "monkeys", "gorillas", "pandas", "koalas",
    "wolves", "foxes", "deer", "moose", "hippos", "rhinos", "giraffes", "zebras",
    "cars", "motorcycles", "bicycles", "skateboards", "guitars", "pianos", "drums", "violins",
    "books", "phones", "laptops", "tablets", "cameras", "watches", "sunglasses", "hats",
    "shoes", "socks", "jackets", "backpacks", "umbrellas", "hammers", "screwdrivers", "saws",
    "knives", "scissors", "pens", "pencils", "paintbrushes", "candles", "lamps", "mirrors",
    "storms", "hurricanes", "tornadoes", "earthquakes", "volcanoes", "tsunamis", "avalanches",
    "sunshine", "rain", "snow", "fog", "wind", "lightning", "thunder", "rainbows",
    "mountains", "valleys", "forests", "deserts", "oceans", "rivers", "lakes", "waterfalls",
    "stars", "planets", "moons", "comets", "asteroids", "galaxies", "black holes",
    "snare drum", "bass drum", "cymbals", "tambourines", "harmonicas", "trumpets", "saxophones",
    "synthesizers", "turntables", "microphones", "speakers", "headphones", "vinyl records",
    "basketball", "football", "baseball", "soccer", "tennis", "golf", "hockey", "volleyball",
    "boxing", "wrestling", "karate", "yoga", "pilates", "running", "swimming", "surfing",
    "skiing", "snowboarding", "skateboarding", "rock climbing", "fishing", "camping", "hiking",
    "robots", "drones", "satellites", "rockets", "spaceships", "ai", "algorithms", "databases",
    "servers", "routers", "modems", "cables", "batteries", "chargers", "processors", "hard drives",
    "refrigerators", "ovens", "microwaves", "blenders", "toasters", "coffee makers", "vacuums",
    "washing machines", "dryers", "dishwashers", "couches", "beds", "chairs", "tables", "desks",
    "pillows", "blankets", "towels", "soap", "shampoo", "toothbrushes", "razors",
    "trucks", "vans", "buses", "trains", "planes", "helicopters", "boats", "yachts", "submarines",
    "tanks", "tractors", "scooters", "segways", "hoverboards",
    "fireworks", "balloons", "confetti", "glitter", "magnets", "puzzles", "dice", "playing cards",
    "rubik's cubes", "yo-yos", "frisbees", "boomerangs", "kites", "bouncy balls", "slinkies",
    "lava lamps", "disco balls", "kazoos", "whoopee cushions", "fidget spinners",
    "chaos", "drama", "revenge", "karma", "destiny", "fate", "luck", "secrets", "mysteries",
    "adventures", "quests", "legends", "myths", "dreams", "nightmares", "paradoxes"
];

// Value is now set server-side, so we don't need to set it in JS
const path = window.location.pathname;

// Update wiggle display with individual letter spans
function updateWiggleDisplay() {
    const text = input.value || '';
    const displayText = text || ' ';

    wiggleDisplay.innerHTML = displayText.split('').map(char =>
        `<span>${char === ' ' ? '&nbsp;' : char}</span>`
    ).join('');

    // Resize wrapper to fit content (enforce minimum width)
    // DISABLED - wrapper sizes naturally to wiggle-display now
    // const tempSpan = document.createElement('span');
    // tempSpan.style.font = window.getComputedStyle(wiggleDisplay).font;
    // tempSpan.style.visibility = 'hidden';
    // tempSpan.style.position = 'absolute';
    // tempSpan.textContent = displayText;
    // document.body.appendChild(tempSpan);
    // inputWrapper.style.width = Math.max(30, tempSpan.offsetWidth + 5) + 'px';
    // document.body.removeChild(tempSpan);
}

// Wait for font to load before sizing
document.fonts.ready.then(() => {
    updateWiggleDisplay();

    // Auto-focus and put cursor at end (only if not submitting from URL)
    if (path === '/' || path === '' || path === '/loading') {
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

// Reset functionality
function resetGame() {
    // Clear cards
    answersContainer.innerHTML = '';
    answersContainer.classList.add('hidden');
    otherAnswersContainer.innerHTML = '';
    otherAnswers.classList.add('hidden');
    loadingContainer.classList.add('hidden');

    // Hide action buttons container
    actionButtons.classList.add('hidden');
    showOthersBtn.classList.add('hidden');

    // Clear graffiti
    clearGraffiti();

    // Reset state
    selectedCard = null;
    currentData = null;
    otherResponses = [];

    // Navigate back to home page
    window.history.pushState({}, '', '/');

    // Set new random word
    input.value = randomWords[Math.floor(Math.random() * randomWords.length)];
    updateWiggleDisplay();

    // Focus input
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
}

// Random button functionality
randomBtn.addEventListener('click', resetGame);

// Reset button functionality
resetBtn.addEventListener('click', resetGame);

// Generate answer cards with random styling
function generateAnswerCards(responses) {
    answersContainer.innerHTML = '';

    // Flatten grouped responses into individual cards (one per model)
    const allCards = [];
    responses.forEach(responseData => {
        responseData.models.forEach((modelName, idx) => {
            allCards.push({
                response: responseData.response,
                model: modelName,
                response_id: responseData.response_ids[idx],
                response_time: responseData.response_time,
                completion_tokens: responseData.completion_tokens
            });
        });
    });

    // Track which response texts we've seen to hide duplicates
    const seenResponses = new Set();

    allCards.forEach((cardData, index) => {
        const card = document.createElement('div');
        card.className = 'answer-card';
        card.dataset.responseId = cardData.response_id;
        card.dataset.response = cardData.response;
        card.dataset.position = index;  // Track display position (0-3)

        // Check if this is a duplicate response - hide it during voting
        const isDuplicate = seenResponses.has(cardData.response);
        if (isDuplicate) {
            card.classList.add('hidden');
        } else {
            seenResponses.add(cardData.response);
        }

        // Random rotation between -1 and 1 degrees
        const rotation = (Math.random() * 2 - 1).toFixed(1);

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
        text.textContent = cardData.response;
        card.appendChild(text);

        // Add model name (top right) - will be revealed on click
        const modelName = document.createElement('div');
        modelName.className = 'model-name';
        modelName.textContent = cardData.model;
        card.appendChild(modelName);

        // Add model stats (bottom right) - will be revealed on click
        const modelStats = document.createElement('div');
        modelStats.className = 'model-stats';
        const timeStr = cardData.response_time ? `${cardData.response_time.toFixed(2)}s` : '...';
        modelStats.textContent = timeStr;
        card.appendChild(modelStats);

        // Click handler - reveal model info and record vote
        card.addEventListener('click', () => selectCard(card, cardData));

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
    otherAnswersContainer.innerHTML = '';
    otherAnswers.classList.add('hidden');
    actionButtons.classList.add('hidden');
    showOthersBtn.classList.add('hidden');

    // Clear graffiti
    clearGraffiti();

    loadingContainer.classList.remove('hidden');
    loadingProgress.textContent = '0/4';
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
            otherResponses = currentData.other_responses || [];  // Store other responses
            generateAnswerCards(currentData.responses);
            answersContainer.classList.remove('hidden');
            return;
        }

        // Poll for status - continues in background until all responses complete
        let contestantsReady = false;
        const pollInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`/api/compete/status?suggestion_id=${currentData.suggestion_id}`);
                const status = await statusResponse.json();

                // Update progress counter
                loadingProgress.textContent = `${status.completed}/${status.total}`;

                // When contestants ready, show them (but keep polling for others)
                if (status.ready && !contestantsReady) {
                    contestantsReady = true;
                    loadingContainer.classList.add('hidden');
                    currentData.responses = status.responses;
                    currentData.contestant_ids = status.contestant_ids;
                    currentData.matchup_id = status.matchup_id;
                    otherResponses = status.other_responses || [];
                    generateAnswerCards(currentData.responses);
                    answersContainer.classList.remove('hidden');
                }

                // Update other responses as they complete
                if (status.ready && status.other_responses) {
                    otherResponses = status.other_responses;

                    // If "other answers" section is visible, update the cards
                    if (!otherAnswers.classList.contains('hidden')) {
                        updateOtherAnswersCards();
                    }

                    // Check if all responses complete
                    const allComplete = otherResponses.every(r => r.status === 'completed');
                    if (allComplete) {
                        clearInterval(pollInterval);
                    }
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
async function selectCard(card, cardData) {
    // If already selected a card, don't allow changing
    if (selectedCard) return;

    selectedCard = card;
    const selectedResponseText = cardData.response;

    // Reveal ALL cards in the main container and their metadata
    const mainCards = answersContainer.querySelectorAll('.answer-card');
    mainCards.forEach(c => {
        // Un-hide any duplicate cards
        c.classList.remove('hidden');

        // Reveal model info for all cards
        c.classList.add('revealed');

        // Disable clicking
        c.style.pointerEvents = 'none';

        // If this card has the same answer as the selected one, mark it selected (for stamp)
        const cardResponse = c.dataset.response;
        if (cardResponse === selectedResponseText) {
            c.classList.add('selected');

            // Add random stamp positioning
            const randomRotation = -18 + Math.random() * 12; // -18deg to -6deg
            const randomOffsetX = -5 + Math.random() * 10; // -5px to 5px
            const randomOffsetY = -8 + Math.random() * 16; // -8px to 8px
            c.style.setProperty('--stamp-rotation', `${randomRotation.toFixed(1)}deg`);
            c.style.setProperty('--stamp-offset-x', `${randomOffsetX.toFixed(1)}px`);
            c.style.setProperty('--stamp-offset-y', `${randomOffsetY.toFixed(1)}px`);
        }
    });

    // Show action buttons with random background positions
    actionButtons.classList.remove('hidden');
    showOthersBtn.classList.remove('hidden');

    // Randomize background positions for action buttons
    const actionBtns = actionButtons.querySelectorAll('.action-btn');
    actionBtns.forEach(btn => {
        const bgX = Math.floor(Math.random() * 100);
        const bgY = Math.floor(Math.random() * 100);
        btn.style.backgroundPosition = `${bgX}% ${bgY}%`;
    });

    // Record vote
    try {
        // Collect positions for all contestants
        const contestant_positions = {};
        mainCards.forEach(c => {
            const responseId = c.dataset.responseId;
            const position = parseInt(c.dataset.position);
            contestant_positions[responseId] = position;
        });

        await fetch('/api/vote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                suggestion_id: currentData.suggestion_id,
                response_ids: [cardData.response_id],
                matchup_id: currentData.matchup_id,
                contestant_ids: currentData.contestant_ids,
                contestant_positions: contestant_positions
            })
        });
    } catch (error) {
        console.error('Error recording vote:', error);
    }
}

// Update "other answers" cards with latest data from otherResponses array
function updateOtherAnswersCards() {
    otherResponses.forEach((responseData) => {
        const card = otherAnswersContainer.querySelector(`[data-model-name="${responseData.model_name}"]`);
        if (!card) return;

        const text = card.querySelector('.answer-text');
        const stats = card.querySelector('.model-stats');

        if (responseData.status === 'completed') {
            // Update text
            if (text.classList.contains('loading-dots')) {
                text.classList.remove('loading-dots');
                text.textContent = responseData.response_text;
            }

            // Update stats
            if (stats.classList.contains('loading-dots')) {
                stats.classList.remove('loading-dots');
                const timeStr = responseData.response_time ? `${responseData.response_time.toFixed(2)}s` : '...';
                stats.textContent = timeStr;
            }
        }
    });
}

// Show other answers button
showOthersBtn.addEventListener('click', () => {
    // Generate cards for other responses immediately (no API call needed)
    otherAnswersContainer.innerHTML = '';
    otherResponses.forEach((responseData, index) => {
        const card = document.createElement('div');
        card.className = 'answer-card revealed';
        card.dataset.modelName = responseData.model_name;

        // Random rotation between -1 and 1 degrees
        const rotation = (Math.random() * 2 - 1).toFixed(1);
        const translateX = Math.floor(Math.random() * 30 - 15);
        const bgX = Math.floor(Math.random() * 100);
        const bgY = Math.floor(Math.random() * 100);
        const slideDir = index % 2 === 0 ? 'slide-left' : 'slide-right';
        card.classList.add(slideDir);

        card.style.transform = `rotate(${rotation}deg) translateX(${translateX}px)`;
        card.style.backgroundPosition = `${bgX}% ${bgY}%`;
        card.style.pointerEvents = 'none';

        // Add text (or loading indicator if pending)
        const text = document.createElement('div');
        text.className = 'answer-text';
        if (responseData.status === 'pending') {
            text.classList.add('loading-dots');
            text.textContent = '';  // Empty, dots will be added by CSS
        } else {
            text.textContent = responseData.response_text;
        }
        card.appendChild(text);

        // Add model name
        const modelName = document.createElement('div');
        modelName.className = 'model-name';
        modelName.textContent = responseData.model_name;
        card.appendChild(modelName);

        // Add model stats (or loading indicator if pending)
        const modelStats = document.createElement('div');
        modelStats.className = 'model-stats';
        if (responseData.status === 'pending') {
            modelStats.classList.add('loading-dots');
            modelStats.textContent = '';  // Empty, dots will be added by CSS
        } else {
            const timeStr = responseData.response_time ? `${responseData.response_time.toFixed(2)}s` : '...';
            modelStats.textContent = timeStr;
        }
        card.appendChild(modelStats);

        otherAnswersContainer.appendChild(card);
    });

    // Show the other answers section
    otherAnswers.classList.remove('hidden');

    // Hide the "Show Other Answers" button
    showOthersBtn.classList.add('hidden');

    // Note: No need to start polling - the initial polling loop
    // already updates otherResponses and calls updateOtherAnswersCards()
});

submitBtn.addEventListener('click', showAnswers);

// Enter key submits
input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        showAnswers();
    }
});

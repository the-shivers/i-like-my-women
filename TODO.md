# Pre-Deployment TODO

## 🚨 CRITICAL - Security
- [x] **Enable rate limiting** to protect API credits
  - Update limiter config in app.py (currently DISABLED at line 22)
  - Add limits to `/api/compete` endpoint (suggest: 10/min per IP)
  - Add limits to `/api/vote` (suggest: 30/min per IP)
  - Change `storage_uri` from `memory://` to redis for Railway persistence
- [x] **Add server-side validation**
  - Enforce max word length (currently only client-side)

## 🚀 Railway Deployment
- [x] **Create proper `Procfile`** (CRITICAL for performance):
  ```
  web: gunicorn --workers=4 --threads=2 --timeout=120 --preload --bind 0.0.0.0:$PORT app:app
  ```
  - `--preload`: Load app before forking workers (helps with initialization)
  - `--workers=4`: Multiple workers for concurrent requests
  - `--threads=2`: Thread pool per worker for better concurrency
  - `--timeout=120`: Allow LLM calls to complete (some models take 15s+)
- [ ] Optional: Create `railway.json` for config

## 🐌 Railway Performance Debugging (if still sluggish after Procfile)
- [ ] **Check Railway logs** for issues:
  - `railway logs --tail` to see real-time logs
  - Look for "Worker timeout" errors
  - Check for database lock messages
  - Watch for slow request warnings
- [ ] **Monitor Railway dashboard metrics**:
  - CPU/Memory usage spikes (throttling?)
  - Service restart frequency
  - Request queue times
- [ ] **Database performance**:
  - Railway's ephemeral disk might be slow for SQLite
  - Consider upgrading to persistent volumes
  - OR migrate to Railway's PostgreSQL addon for production
- [ ] **Cold start issues**:
  - Free/Hobby tier might pause service after inactivity
  - Enable "Always On" if available (paid feature)
  - Check restart policies
- [ ] **Network latency**:
  - Try deploying to different Railway region
  - Test if closer region to OpenRouter API helps
- [ ] **If all else fails**: Profile with `--log-level debug` in Procfile

## 💾 Random Words Curation
- [ ] Change the random words to have more funny ones and remove unfunny ones
  - Some words have no good answers
  - Need to review and improve the list

## 🎨 UI Polish
- [x] **Make first paint look nicer / Fix asset loading**
  - Converted all images to WebP (88% size reduction: 1.97MB → 230KB)
  - Page now loads assets ~7x faster (40s → 5-6s at 3G speeds)
  - parch2: 736KB→47KB, wood: 604KB→32KB, brick: 150KB→84KB
  - graffiti icons: ~120KB→45KB, checkstamp: 356KB→21KB
- [x] **Self-host fonts for better performance**
  - Eliminated Google Fonts CDN dependency (saves DNS lookup + TLS handshake)
  - All 6 fonts now served locally (~161KB total)
  - Added font-display: swap for instant text visibility
  - Preloaded critical fonts for above-the-fold content
  - Removed 200-400ms of cross-origin latency
- [x] **Hide text until fonts are loaded**
  - Current font-display: swap causes ugly layout shift as fonts load
  - Changed font-display: swap → font-display: block in all @font-face declarations
  - Text now remains invisible until custom fonts load (no layout shift)
  - Updated in both index.html and stats.html
- [x] **Fix cards showing text before parchment background on mobile**
  - Issue: On slow mobile connections, card text renders before parch2.webp background loads
  - Even though parch2.webp is preloaded, CSS background-image doesn't block rendering
  - Fix: Added Promise-based parchment preload in both app.js and modal.js
  - Cards and about modal now await parchment loading before becoming visible
- [x] **Fix about modal using old parch2.jpg instead of parch2.webp**
  - Issue: About modal takes ages to load on mobile
  - Root cause: Still using parch2.jpg (736KB) instead of parch2.webp (47KB) - 15x larger!
  - Fix: Updated modal.js line 21 to use parch2.webp
  - This will make about modal load 15x faster on mobile
- [x] **Fix stamp delay on mobile (first click only)**
  - Issue: checkstamp.webp has delay on first click, instant on successive clicks
  - Root cause: Preload has fetchpriority="low" so browser doesn't load it until needed
  - Fix: Removed fetchpriority="low" from checkstamp.webp preload in index.html line 37
- [x] **Fix graffiti spilling into black letterbox on very wide monitors**
  - Issue: On very wide screens, black letterboxes appear (good), but graffiti drawn near edge of center panel spills over into black areas where it appears super bright
  - Root cause: .stage has max-width 1600px but no overflow clipping, graffiti icons can extend beyond boundaries
  - Fix: Added overflow: hidden to .stage element - graffiti now clips at stage boundaries
- [ ] Adjust spotlight/floodlight if desired
  - Edit `.spotlight-overlay` radial gradients in index.html & stats.html
- [x] move fade down slightly

## 🧹 Code Cleanup (Optional)
- [x] Clean up debug print() statements (lines 206, 275, 293 in app.py)
  - Or gate them behind debug flag

## 🤖 Model Updates
- [x] **Add Claude Haiku 4.5 model**
  - Add to MODELS list in app.py
  - Test response time to see if it qualifies (need <4s avg)
- [x] **Check BYOK (Bring Your Own Key) setup**
  - Verify cost tracking is working correctly
  - Ensure upstream_inference_cost is being captured properly

## 📊 Analytics Features
- [x] **Track display position for votes**
  - Add `display_position` column to appearances table (0-3 or 1-4)
  - Send position data from frontend when voting
  - Analyze position bias: Do people pick top option more? Bottom?
  - Calculate win rate by position to detect order effects

## 🐛 Bug Fixes
- [x] **Fixed 404 error on "Show Other Answers"**
  - Issue: Clicking "Show Other Answers" on NEW words caused 404s
  - Root cause: Initial polling stopped when contestants ready, then tried to restart polling later
  - Fix: Keep initial polling running in background until ALL models complete
  - "Show Other Answers" now just reveals already-loaded data (no new polling)
- [x] **Removed redundant second polling loop**
  - Issue: Extra API call after clicking "Show Other Answers"
  - Root cause: Button click started a second polling loop (was redundant with initial polling)
  - Fix: Removed `startPollingOtherResponses()` function entirely
  - Initial polling now handles everything - cleaner, more efficient
- [ ] **Fix null reference error + add resilient retry logic** 🎯 FINAL ITEM

  ### Problem Description
  When Railway has transient issues (502, restarts, etc), the frontend crashes:
  - Initial `/api/compete` returns 502 (but with valid JSON)
  - Frontend doesn't handle failure → `currentData` becomes null
  - Polling loop accesses `currentData.suggestion_id` → crashes with "Cannot read properties of null"
  - Loading spinner shows "undefined/undefined"
  - Continues polling `/api/compete/status?suggestion_id=undefined` → 404 errors forever

  ### How to Replicate (Pick One)

  **Option 1: Browser DevTools (Easiest)**
  1. Open DevTools → Network tab
  2. Right-click network panel → "Block request URL"
  3. Add pattern: `*/api/compete*`
  4. Submit a word → Bug triggers immediately

  **Option 2: Random 502 Injection (Most Realistic)**
  Add this to `app.py` line 386 in `compete()` function:
  ```python
  # TEMPORARY: Force 502 for testing
  import random
  if random.random() < 0.5:  # 50% chance
      return jsonify({'error': 'Simulated 502'}), 502
  ```

  **Option 3: Kill Backend Mid-Request**
  1. Start local server
  2. Submit word, then quickly Ctrl+C the server
  3. Frontend gets network error → bug triggers

  ### Proposed Solution (Two-Layer Defense)

  **Layer 1: Automatic Retries (Handles 95% of transient failures)**
  - Add `fetchWithRetry()` helper function
  - Retry on: 502, 503, 504, network errors
  - Don't retry on: 400, 429 (rate limit), 401, 403
  - Exponential backoff: 1s, 2s, 4s (3 total attempts)
  - User just sees loading spinner - seamless experience

  **Layer 2: Null Safety Checks (Final safety net)**
  - Add null checks before accessing `currentData.suggestion_id`
  - Graceful error handling if all retries fail
  - Display user-friendly error message instead of crash
  - Add 2-minute timeout on polling loop to prevent infinite requests

  ### Implementation Checklist
  - [ ] Add `fetchWithRetry()` function to app.js
  - [ ] Wrap `/api/compete` call with retry logic
  - [ ] Add null checks in polling loop
  - [ ] Add 2-minute timeout to polling
  - [ ] Test with Option 1 (DevTools blocking)
  - [ ] Test with Option 2 (Random 502s)
  - [ ] Verify graceful degradation when all retries fail

## 🐛 Testing
- [ ] **GET JUGGY TO HELP DEBUG**
  - Test rate limiting
  - Test under load
  - Check for any edge cases

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
- [ ] **Fix null reference error on page load**
  - Issue: "Cannot read properties of null (reading 'suggestion_id')" popup
  - Shows "undefined/undefined" in loading spinner
  - Happens when initial /api/compete request fails or returns unexpected data
  - Polling loop tries to access currentData.suggestion_id when currentData is null
  - Need safety checks before accessing currentData in polling loop
- [ ] **Fix infinite polling causing loading cursor on Windows**
  - Issue: Loading cursor (pointer with spinner) persists even when page looks fine
  - Root cause: Polling loop runs forever if any model fails or times out
  - Polling only stops when ALL otherResponses reach status='completed'
  - If one model hangs, browser keeps making requests every 500ms forever
  - Need: Timeout on polling loop (e.g., stop after 2 minutes max)

## 🐛 Testing
- [ ] **GET JUGGY TO HELP DEBUG**
  - Test rate limiting
  - Test under load
  - Check for any edge cases

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
- [ ] Add Redis service to Railway project (for rate limiting)

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

## 🐛 Testing
- [ ] **GET JUGGY TO HELP DEBUG**
  - Test rate limiting
  - Test under load
  - Check for any edge cases

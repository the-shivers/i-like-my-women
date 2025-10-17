# Pre-Deployment TODO

## 🚨 CRITICAL - Security
- [ ] **Enable rate limiting** to protect API credits
  - Update limiter config in app.py (currently DISABLED at line 22)
  - Add limits to `/api/compete` endpoint (suggest: 10/min per IP)
  - Add limits to `/api/vote` (suggest: 30/min per IP)
  - Change `storage_uri` from `memory://` to redis for Railway persistence
- [ ] **Add server-side validation**
  - Enforce max word length (currently only client-side)

## 🚀 Railway Deployment
- [ ] **Create proper `Procfile`** (CRITICAL for performance):
  ```
  web: gunicorn --workers=4 --threads=2 --timeout=120 --preload --bind 0.0.0.0:$PORT app:app
  ```
  - `--preload`: Load app before forking workers (helps with initialization)
  - `--workers=4`: Multiple workers for concurrent requests
  - `--threads=2`: Thread pool per worker for better concurrency
  - `--timeout=120`: Allow LLM calls to complete (some models take 15s+)
- [ ] Optional: Create `railway.json` for config
- [ ] Add Redis service to Railway project (for rate limiting)
- [ ] Set environment variables in Railway:
  - `FLASK_DEBUG=False`
  - `FLASK_SECRET_KEY` (secure random key)
  - `OPENROUTER_API_KEY`
- [ ] **API key email for OpenAI - need to deal with this**

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

## 💾 Database Seeding
- [ ] Seed 10-15 funny words with all model responses:
  - Suggested words: coffee, whiskey, toaster, pizza, drums, shoes, wine, beer, cats, dogs, burgers, bacon, tacos, sushi, donuts
  - Gives visitors immediate content to explore

## 🎨 UI Polish
- [ ] **Make first paint look nicer / Fix asset loading**
  - Currently ugly as bricks load in piecewise
  - Show spinner on black background until all assets are ready
  - Only paint page once everything is loaded (wait for images to load)
  - Make loading elegant and smooth
- [ ] Adjust spotlight/floodlight if desired
  - Edit `.spotlight-overlay` radial gradients in index.html & stats.html

## 🧹 Code Cleanup (Optional)
- [ ] Clean up debug print() statements (lines 206, 275, 293 in app.py)
  - Or gate them behind debug flag

## 🤖 Model Updates
- [ ] **Add Claude Haiku 4.5 model**
  - Add to MODELS list in app.py
  - Test response time to see if it qualifies (need <4s avg)
- [ ] **Check BYOK (Bring Your Own Key) setup**
  - Verify cost tracking is working correctly
  - Ensure upstream_inference_cost is being captured properly

## 📊 Analytics Features
- [ ] **Track display position for votes**
  - Add `display_position` column to appearances table (0-3 or 1-4)
  - Send position data from frontend when voting
  - Analyze position bias: Do people pick top option more? Bottom?
  - Calculate win rate by position to detect order effects

## 🐛 Testing
- [ ] **GET JUGGY TO HELP DEBUG**
  - Test rate limiting
  - Test under load
  - Check for any edge cases

## ⚠️ CRITICAL NOTE
**Without rate limiting, someone could easily burn through your OpenRouter credits in minutes. This MUST be done before deploying.**

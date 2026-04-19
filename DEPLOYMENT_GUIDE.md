# Tier 3 Deployment & Integration Guide

## Quick Start (For Render Deployment)

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

The new Tier 3 dependencies are:
- `selenium==4.15.2`
- `beautifulsoup4==4.12.2`  
- `webdriver-manager==4.0.1`

### 2. No Configuration Changes Needed
The system auto-detects:
- Chrome/Chromium installation (pre-installed on Render Linux)
- College queries via intent detection
- When to trigger Tier 3 lookup

### 3. Test Locally (Optional)
```bash
python backend/tests/test_tier3.py
```

## Deployment to Render

### Prerequisites
✅ Render already has Chrome/Chromium installed  
✅ Selenium drivers are auto-downloaded by webdriver-manager  
✅ No additional system packages needed  

### Render Configuration
Your `render.yaml` or environment doesn't need changes. The app works as-is:

```yaml
# No changes needed - existing config works
services:
  - type: web
    name: aerochat-rag
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Deployment Steps
```bash
# 1. Commit changes
git add -A
git commit -m "Add Tier 3 support"

# 2. Push to GitHub
git push origin main

# 3. Render auto-deploys (if connected)
# Or manually trigger deployment in Render dashboard
```

## Performance Considerations

### Tier 3 Latency
- **Web Search**: 2-5 seconds
- **Form Automation**: 5-15 seconds  
- **Total**: 8-25 seconds per Tier 3 request

This is acceptable for non-real-time use but noticeable for users.

### Optimization Tips
1. **Cache known colleges** - Add more hardcoded mappings in `tier3_web_search.py`
2. **Limit retry attempts** - Set timeout shorter if calculator unreachable
3. **Batch queries** - Process multiple college searches together
4. **Monitor usage** - Log Tier 3 hits vs Tier 1/2 hits

## Monitoring & Logs

### Key Log Messages to Watch
```
🔍 [RAG] Retrieving for: [query]            # RAG retrieval
📚 [TIER3] Attempting Tier 3 lookup...      # Tier 3 triggered
   [TIER3] Lookup completed: success        # Tier 3 success
🧠 [LLM] Generating response...             # LLM generation
```

### Error Logs
```
[TIER3] Lookup error: [error message]       # Web search/automation failed
❌ [ORCHESTRATOR ERROR]                      # Critical error
```

## Troubleshooting

### Problem: "Chrome driver not found"
**Solution:**  
- webdriver-manager should auto-download, but if it fails:
  ```bash
  pip install --upgrade webdriver-manager
  ```
- Ensure `/tmp` has ~500MB free space

### Problem: "Timeout - college website not loading"
**Solution:**  
- College website may be slow or blocking automated access
- Increase timeout in `tier3_form_automation.py`: `self.timeout = 15`
- Add college to hardcoded list if available

### Problem: "Form automation returns None for NPC"
**Solution:**  
- College's calculator page structure is unique
- Manually update regex patterns in `_extract_npc_result()`
- Report to team with screenshot for common colleges

### Problem: "Web search finding wrong college"
**Solution:**  
- Add state to search: `search_college_npc(college, state="Tamil Nadu")`
- Improve college name parsing in `extract_college_details()`

## Rolling Back (If Issues)

If Tier 3 causes problems:

### Option 1: Disable Tier 3 (Keep Tier 1/2 working)
In `chat_orchestrator.py`, comment out:
```python
# tier3_result = await self.tier3.lookup_npc(user_message)
```

### Option 2: Rollback Commit
```bash
git revert HEAD  # Revert the Tier 3 commit
git push origin main
```

## Monitoring Render Logs

### View logs
```bash
# Render Dashboard → Services → aerochat-rag → Logs
# Or via CLI:
render logs --service aerochat-rag-api
```

### What to look for
- Selenium errors (ChromeDriver issues)
- Network timeouts (slow college websites)
- Form extraction failures (HTML parsing issues)
- Success rate of Tier 3 lookups

## Cost Impact

No additional costs for Tier 3:
- ✅ Selenium = Free (open source)
- ✅ Chrome = Pre-installed on Render
- ✅ Web search = Free (DuckDuckGo)
- ✅ No external APIs used

## Next Steps

### Phase 2 Improvements (Future)
1. **Add more college integrations** - Partner with popular colleges for APIs
2. **Cache results** - Store NPC results for repeat queries
3. **Improve parsing** - Use ML to detect form fields automatically
4. **Load balancing** - Use proxy rotation to avoid rate limiting

### Monitoring Dashboard (Future)
- Track Tier 1/2 vs Tier 3 hit rates
- Monitor Tier 3 success/failure ratio
- Alert on high latency (>30s)
- Dashboard showing most searched colleges

## Contact & Support

For deployment issues:
1. Check Render logs for specific errors
2. Verify Chrome is available: `which chromium-browser` or `which google-chrome`
3. Test locally before deploying: `python backend/tests/test_tier3.py`
4. Report issues with full log context

---

**Status:** ✅ Production Ready  
**Last Updated:** April 2026  
**Tested On:** Render (Linux), Local (Windows)

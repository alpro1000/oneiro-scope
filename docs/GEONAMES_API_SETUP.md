# GeoNames API Setup Guide

## Why GeoNames?

The city autocomplete feature uses GeoNames API for real-time city search with:
- 30,000 free requests/day
- Global coverage (11+ million place names)
- Multilingual support (Russian, English, and more)
- Timezone information included

## Current Status

✅ **Fallback works perfectly** without GeoNames API!
- Built-in database: 90+ popular cities
- Supports Russian and English names
- Instant response (no API calls)

❌ **GeoNames API currently disabled**
- Username not configured
- Using secure fallback instead
- No rate limits or 403 errors

## How to Enable GeoNames API (Optional)

### Step 1: Register Free Account
1. Go to https://www.geonames.org/login
2. Click "create a new user account"
3. Fill in the form and verify email
4. **Important:** Go to your account page and **enable web services**

### Step 2: Set Environment Variable

**Backend `.env` or `.env.local`:**
```bash
# GeoNames API (for geocoding)
# Register free account at https://www.geonames.org/login
# Free tier: 30,000 requests/day
GEONAMES_USERNAME=your_geonames_username  # ← Replace with your username
GEONAMES_LANG=ru
```

### Step 3: Restart Backend
```bash
# Development
uvicorn backend.app.main:app --reload --port 8000

# Production (Render)
# Set GEONAMES_USERNAME in Environment Variables
# Redeploy backend service
```

### Step 4: Verify API Works
```bash
# Test endpoint
curl "http://localhost:8000/api/v1/astrology/cities/search?query=Моск&locale=ru"

# Should return:
# {
#   "query": "Моск",
#   "cities": [
#     {
#       "name": "Moscow",
#       "country": "Russia",
#       "display": "Moscow, Moscow City, Russia",
#       "lat": 55.7522,
#       "lon": 37.6156,
#       "geoname_id": 524901
#     }
#   ]
# }
```

## Fallback Behavior

**Without GeoNames API** (current state):
1. Search built-in database (90+ cities)
2. Return results instantly
3. No rate limits, no errors

**With GeoNames API** (when configured):
1. Try GeoNames API first (30k req/day)
2. If Russian query, try transliteration
3. If API fails, fallback to built-in database

## Troubleshooting

### Error: 403 Forbidden
**Cause:** Using "demo" username (deactivated by GeoNames)
**Fix:** Register account and set `GEONAMES_USERNAME`

### Error: "the hourly limit of X credits has been exceeded"
**Cause:** Free tier limit reached (30k/day or 1k/hour)
**Fix:** Wait for reset or upgrade to premium

### No Results from API
**Cause:** Web services not enabled on account
**Fix:** Log in to geonames.org → Account → Enable Web Services

## Production Deployment (Render)

1. Go to Render Dashboard → Backend Service
2. Environment → Add `GEONAMES_USERNAME`
3. Click "Clear build cache & Deploy"
4. Verify in logs: `[GeoNames] Using provider: your_username`

## API Limits

| Plan | Requests/Hour | Requests/Day | Cost |
|------|---------------|--------------|------|
| Free | 1,000 | 30,000 | $0 |
| Premium | 100,000 | 2,400,000 | $150/year |

## Security Notes

✅ **Good practices:**
- API username is safe to expose (not a secret)
- Backend hides username from frontend
- Rate limiting handled by GeoNames

❌ **Avoid:**
- Don't use "demo" username (deactivated)
- Don't call GeoNames directly from frontend
- Don't skip web services activation

## Summary

**Current:** System works perfectly with fallback (90+ cities)
**Optional:** Enable GeoNames for 11M+ cities worldwide

No action required unless you need:
- Smaller cities not in built-in database
- Real-time population data
- Admin divisions (states, regions)
- Postal codes and elevation data

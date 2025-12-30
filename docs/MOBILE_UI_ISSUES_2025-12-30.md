# Mobile UI Issues Analysis - 2025-12-30

**Status:** 🔴 Critical UI/UX Issues Found
**Platform:** Mobile (iPhone/Safari)
**Affected:** Natal Chart, Horoscope pages

---

## 📱 Issues from Screenshots

### Issue #1: ✅ FIXED - Lunar Phase Shows Key Instead of Name

**Problem:**
```
☽ waxing_gibbous День 11
```
Instead of:
```
☽ Растущая Луна День 11
```

**Root Cause:**
- Backend returned `lunar_phase: "waxing_gibbous"` (phase key)
- Frontend displayed raw key instead of human-readable name

**Fix Applied:** ✅
- Added `lunar_phase_display` field to `HoroscopeResponse` schema
- Backend now maps phase keys to readable names:
  - `waxing_gibbous` → `"Растущая Луна"` (RU)
  - `waxing_gibbous` → `"Waxing Gibbous"` (EN)

**Files Changed:**
- `backend/services/astrology/schemas.py` - Added field
- `backend/services/astrology/service.py` - Added phase mapping

**Frontend TODO:**
```tsx
// Use lunar_phase_display instead of lunar_phase
<Text>{horoscope.lunar_phase_display}</Text>  // ✅ "Растущая Луна"
// NOT
<Text>{horoscope.lunar_phase}</Text>  // ❌ "waxing_gibbous"
```

---

### Issue #2: ⚠️ FRONTEND - Planet/Sign Symbols Mixed with Text

**Problem:**
```
☉ Солнце
♐ Стрелец
☽ Луна
♌ Лев
```

Symbols (☉, ♐, ☽, ♌) displayed **alongside** text instead of **instead of** text.

**Root Cause:**
- Frontend likely concatenating emoji + text
- Should display **either** emoji **or** text, not both

**Expected:**
```
Солнце в Стрельце
Луна во Льве
```

**Frontend Fix Needed:**
```tsx
// ❌ Wrong
<Text>{PLANET_EMOJI[planet]} {PLANET_NAMES[planet]}</Text>

// ✅ Correct - Choose ONE display mode
<Text>{PLANET_NAMES[planet]}</Text>  // Text-only
// OR
<Text>{PLANET_EMOJI[planet]}</Text>  // Emoji-only
```

---

### Issue #3: ⚠️ FRONTEND - Aspect Abbreviations

**Problem:**
```
Ключевые аспекты:
- С trine М
- С conjunction Н
- Л square В
```

**Expected:**
```
Ключевые аспекты:
- Солнце в тригоне с Меркурием
- Солнце в соединении с Нептуном
- Луна в квадрате с Венерой
```

**Root Cause:**
- Backend returns aspect data correctly
- Frontend displays single-letter abbreviations:
  - С = Солнце (Sun)
  - М = Меркурий (Mercury)
  - Н = Нептун (Neptune)
  - Л = Луна (Moon)
  - В = Венера (Venus)

**Backend Response (Correct):**
```json
{
  "aspects": [
    {
      "planet1": "SUN",
      "planet2": "MERCURY",
      "aspect_type": "trine"
    }
  ]
}
```

**Frontend Fix Needed:**
```tsx
// Planet name mapping
const PLANET_NAMES_RU = {
  SUN: "Солнце",
  MOON: "Луна",
  MERCURY: "Меркурий",
  VENUS: "Венера",
  MARS: "Марс",
  // ...
};

// Aspect type mapping
const ASPECT_NAMES_RU = {
  conjunction: "в соединении с",
  trine: "в тригоне с",
  square: "в квадрате с",
  opposition: "в оппозиции с",
  sextile: "в секстиле с",
};

// Render
aspects.map(a =>
  `${PLANET_NAMES_RU[a.planet1]} ${ASPECT_NAMES_RU[a.aspect_type]} ${PLANET_NAMES_RU[a.planet2]}`
)
```

---

### Issue #4: ⚠️ FRONTEND - Period Buttons Don't Fit Screen

**Problem:**
```
┌──────────────────────────────────────┐
│ [Ежедневный] [Еженедельный] [Ежемес│
└──────────────────────────────────────┘
        ↑ Text cut off, no scroll
```

**Root Cause:**
- Buttons too wide for mobile screen
- No responsive layout
- Text truncation

**Frontend Fix Needed:**

**Option 1: Abbreviate Text**
```tsx
const PERIOD_LABELS = {
  daily: "День",      // was: Ежедневный
  weekly: "Неделя",   // was: Еженедельный
  monthly: "Месяц",   // was: Ежемесячный
  yearly: "Год",      // was: Ежегодный
};
```

**Option 2: Stack Vertically on Mobile**
```tsx
<ButtonGroup
  orientation={isMobile ? "vertical" : "horizontal"}
>
  <Button>Ежедневный</Button>
  <Button>Еженедельный</Button>
  <Button>Ежемесячный</Button>
  <Button>Ежегодный</Button>
</ButtonGroup>
```

**Option 3: Horizontal Scroll**
```css
.period-buttons {
  display: flex;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  gap: 8px;
}
```

---

## 📊 Summary

| Issue | Type | Status | Fix Location |
|-------|------|--------|--------------|
| **Lunar phase key instead of name** | Backend | ✅ **FIXED** | backend/services/astrology/service.py |
| **Planet symbols + text** | Frontend | ⚠️ **TODO** | frontend/components/NatalChart.tsx |
| **Aspect abbreviations** | Frontend | ⚠️ **TODO** | frontend/components/Aspects.tsx |
| **Period buttons overflow** | Frontend | ⚠️ **TODO** | frontend/components/HoroscopeSelector.tsx |

---

## 🔧 Backend Changes Made

### 1. schemas.py
```python
class HoroscopeResponse(BaseModel):
    lunar_phase: str  # Key like "waxing_gibbous"
    lunar_phase_display: Optional[str] = None  # ✅ NEW - "Растущая Луна"
```

### 2. service.py
```python
# Map lunar phase to human-readable name
phase_names = {
    "ru": {
        "waxing_gibbous": "Растущая Луна",
        # ... all phases
    },
    "en": { ... }
}
lunar_phase_display = phase_names[locale][lunar_phase]

return HoroscopeResponse(
    lunar_phase=lunar_phase,
    lunar_phase_display=lunar_phase_display,  # ✅ NEW
    # ...
)
```

---

## 🎨 Frontend Changes Needed

### Priority 1: Use lunar_phase_display

**File:** All horoscope components

**Change:**
```diff
- <Text>{horoscope.lunar_phase}</Text>
+ <Text>{horoscope.lunar_phase_display}</Text>
```

### Priority 2: Fix Planet/Sign Display

**File:** `frontend/components/NatalChart.tsx` (or similar)

**Add mapping:**
```tsx
const PLANET_NAMES: Record<string, Record<string, string>> = {
  ru: {
    SUN: "Солнце",
    MOON: "Луна",
    MERCURY: "Меркурий",
    VENUS: "Венера",
    MARS: "Марс",
    JUPITER: "Юпитер",
    SATURN: "Сатурн",
    URANUS: "Уран",
    NEPTUNE: "Нептун",
    PLUTO: "Плутон",
  },
  en: { /* ... */ }
};

const SIGN_NAMES: Record<string, Record<string, string>> = {
  ru: {
    ARIES: "Овен",
    TAURUS: "Телец",
    GEMINI: "Близнецы",
    CANCER: "Рак",
    LEO: "Лев",
    VIRGO: "Дева",
    LIBRA: "Весы",
    SCORPIO: "Скорпион",
    SAGITTARIUS: "Стрелец",
    CAPRICORN: "Козерог",
    AQUARIUS: "Водолей",
    PISCES: "Рыбы",
  },
  en: { /* ... */ }
};
```

**Render:**
```tsx
{planets.map(p => (
  <Text>
    {PLANET_NAMES[locale][p.planet]} в {SIGN_NAMES[locale][p.sign]}
  </Text>
))}
```

### Priority 3: Fix Aspect Display

**File:** `frontend/components/Aspects.tsx`

```tsx
const ASPECT_NAMES: Record<string, Record<string, string>> = {
  ru: {
    conjunction: "в соединении с",
    sextile: "в секстиле с",
    square: "в квадрате с",
    trine: "в тригоне с",
    opposition: "в оппозиции с",
  },
  en: { /* ... */ }
};

{aspects.map(a => (
  <Text>
    {PLANET_NAMES[locale][a.planet1]} {ASPECT_NAMES[locale][a.aspect_type]} {PLANET_NAMES[locale][a.planet2]}
  </Text>
))}
```

### Priority 4: Fix Period Buttons

**File:** `frontend/components/HoroscopePeriodSelector.tsx`

**Option A: Abbreviate**
```tsx
const PERIOD_LABELS_SHORT = {
  ru: {
    daily: "День",
    weekly: "Неделя",
    monthly: "Месяц",
    yearly: "Год",
  }
};
```

**Option B: Scroll**
```tsx
<ScrollView horizontal showsHorizontalScrollIndicator={false}>
  {periods.map(p => <Button>{p}</Button>)}
</ScrollView>
```

---

## ✅ Testing Checklist

After frontend fixes:

- [ ] Lunar phase shows "Растущая Луна" not "waxing_gibbous"
- [ ] Planets show "Солнце в Стрельце" not "☉ Солнце ♐ Стрелец"
- [ ] Aspects show full text not abbreviations
- [ ] Period buttons fit on screen and are clickable

---

## 📁 Related Files

**Backend (Fixed):**
- `backend/services/astrology/schemas.py`
- `backend/services/astrology/service.py`

**Frontend (Needs Fixes):**
- `frontend/components/NatalChart.tsx` (or wherever natal chart displayed)
- `frontend/components/Horoscope.tsx` (or wherever horoscope displayed)
- `frontend/components/Aspects.tsx` (or wherever aspects displayed)
- `frontend/components/PeriodSelector.tsx` (or wherever period buttons)

---

**Status:** Backend fixes committed. Frontend changes required for full resolution.
**Commit:** `9f44e19` - "fix: add lunar_phase_display field for human-readable phase names"

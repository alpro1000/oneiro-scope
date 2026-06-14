# OneiroScope Mobile (iOS + Android)

Strategy: **Capacitor** wraps the existing Next.js frontend (static
export) in native iOS and Android shells. One web codebase, two app
stores, no React Native rewrite.

This is the fastest path from "web ready" to "shipped app" for a solo
founder. Native features (push, biometric auth, secure storage, share
sheet) are provided by Capacitor plugins.

---

## 1. Why Capacitor (not React Native, not PWA)

| Option | Speed to ship | Native polish | Code reuse |
|---|---|---|---|
| **Capacitor (chosen)** | Days | Good | 100% web |
| React Native rewrite | Months | Best | 0% |
| PWA only | Hours | Mediocre (no App Store) | 100% web |
| Expo + WebView | Days | Same as Capacitor | 100% web |

Capacitor gives you store presence (App Store + Play Store) which is
required for credibility in this market segment ("научная астрология
доступна как приложение").

---

## 2. Prerequisites

- macOS for iOS builds (Xcode 15+); Android builds work on any OS.
- Node 18+.
- Apple Developer account ($99/yr) — sign up at
  https://developer.apple.com.
- Google Play Console account ($25 one-time) — sign up at
  https://play.google.com/console.

---

## 3. Set up the Capacitor wrapper

```bash
mkdir mobile && cd mobile
npm init -y
npm install @capacitor/core @capacitor/cli
npx cap init "OneiroScope" "app.oneiroscope" --web-dir="../frontend/out"

# Native plugins we'll use:
npm install \
  @capacitor/preferences \
  @capacitor/share \
  @capacitor/push-notifications \
  @capacitor/app-launcher \
  @capacitor/status-bar \
  @capacitor/splash-screen \
  @capacitor/haptics

# Add native platforms
npx cap add ios
npx cap add android
```

Configure `mobile/capacitor.config.ts`:

```typescript
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.oneiroscope',
  appName: 'OneiroScope',
  webDir: '../frontend/out',
  server: {
    // For production: bundle assets locally (no remote URL).
    // For dev: set url to a tunneled localhost (ngrok / Tailscale).
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      backgroundColor: '#7c3aed',
      androidSpinnerStyle: 'small',
      iosSpinnerStyle: 'small',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
};

export default config;
```

---

## 4. Build the web for static export

Next.js needs to be set to **static export mode** for Capacitor to bundle
the assets into the app:

```javascript
// frontend/next.config.js
module.exports = {
  output: 'export',                  // <- enables static export
  images: { unoptimized: true },     // required for export
  // ... rest of config
};
```

Then build:

```bash
cd frontend
npm run build       # produces frontend/out/
cd ../mobile
npx cap sync        # copies frontend/out → ios/App/App/public, etc.
```

⚠ Anything that requires an SSR-only Next.js feature (server actions,
streaming SSR, middleware-based locale routing) must be reworked for
client-side. The lunar SSR fetch in `frontend/app/[locale]/(calendar)`
needs to become a client fetch from `NEXT_PUBLIC_API_URL`.

---

## 5. iOS build (Xcode)

```bash
npx cap open ios
```

Xcode opens. Then:

1. **Signing & Capabilities** → Team → your Apple Developer account.
2. **Identifiers** in Apple Developer portal → register
   `app.oneiroscope`.
3. **Push Notifications** capability (if enabled) → APNs key
   (Apple Developer → Keys → +).
4. Product → Archive → Window → Organizer → Distribute App →
   App Store Connect → Upload.
5. **TestFlight** → invite internal testers; iterate.
6. **App Store** → submit for review (App Store Connect → Apps → New
   App → fill all metadata).

### iOS review hot-spots

- **In-App Purchases**: Apple **requires** native IAP for any digital
  goods (no web-checkout shortcuts). Plan two release tracks:
  - **TestFlight first** (no IAP required for free apps).
  - **App Store Premium release**: implement
    `RevenueCat` ($0/mo until $2.5k revenue then 1%) to handle native
    IAP and bridge entitlements to your backend. RevenueCat webhook
    posts to `/api/v1/billing/revenuecat-webhook` (TODO endpoint).
- **Sign in with Apple** — required if you offer any third-party sign-in
  (Google, etc.). For email/password only, not required.
- **Privacy nutrition label** — fill out in App Store Connect: data
  collected = email, dream text, birth data; purpose = service core.

---

## 6. Android build (Android Studio)

```bash
npx cap open android
```

Android Studio opens. Then:

1. Build → Generate Signed Bundle → AAB.
2. Create a release keystore (`keytool -genkey ...`). **Back this up**;
   losing it means you can't update the app.
3. Google Play Console → Create app → Internal Testing track → upload
   AAB.
4. **Production release** after internal testing settles.

### Google Play hot-spots

- **Google Play Billing**: same rule as Apple — digital goods must use
  native billing for in-app subscriptions. RevenueCat covers both.
- **Data Safety form**: similar to Apple's privacy label.
- **Target SDK**: keep up with Play's annual target SDK requirement
  (currently 34 / Android 14).

---

## 7. Native plugins we'll actually use

| Need | Plugin |
|---|---|
| Persist JWT securely | `@capacitor/preferences` (encrypted on iOS Keychain, Android Keystore) |
| Voice input | Web Speech API on Android; **iOS Safari has no Web Speech** → use `@capacitor-community/speech-recognition` |
| Share natal chart | `@capacitor/share` (native share sheet) |
| Push for daily horoscope | `@capacitor/push-notifications` + Firebase Cloud Messaging |
| Splash screen | `@capacitor/splash-screen` |
| Status bar | `@capacitor/status-bar` |

---

## 8. Backend changes needed for mobile

Already done:
- `/auth/register` + `/auth/login` (Phase 6.A).
- `/billing/checkout` returns hosted URL (works in WebView).

Still TODO:
- `POST /api/v1/billing/revenuecat-webhook` for iOS/Android IAP
  entitlement sync.
- Push notification preference endpoint + APNs/FCM provider keys.
- Deep links: `oneiroscope://natal/<id>`, `oneiroscope://dream/<id>`.

---

## 9. App Store Connect metadata (5 locales)

Each store listing needs:

- **App name** — translate per locale.
- **Subtitle** (iOS, 30 chars) / **Short description** (Android, 80 chars).
- **Description** — long-form copy. 5 versions (RU/EN/DE/ES/FR).
- **Keywords** (iOS, 100 chars) — research with Sensor Tower / data.ai.
- **Screenshots** — 5 per device class × 5 locales = 25 minimum.
  Generate with [Fastlane](https://fastlane.tools) or pay a designer.
- **Privacy policy URL** — `https://oneiroscope.app/privacy`.
- **Support URL** — `https://oneiroscope.app/support`.

---

## 10. Timeline estimate

| Milestone | Days (solo) |
|---|---|
| Capacitor + static export working | 1 |
| iOS TestFlight upload | 1 |
| Android internal track upload | 0.5 |
| Screenshot generation (5 locales) | 1 |
| Submit iOS to App Store | 0.5 |
| Submit Android to Play Store | 0.5 |
| **Total active work** | **≈ 5 days** |
| Apple review queue | 1-7 days (avg 2 days in 2025) |
| Google review queue | 1-3 days |

After approval, daily horoscope push notifications + RevenueCat IAP can
be added iteratively as updates.

---

## 11. Cost summary (mobile, ongoing)

| Item | Cost |
|---|---|
| Apple Developer | $99/yr |
| Google Play | $25 one-time |
| RevenueCat | Free until $2.5k MRR, 1% after |
| Firebase Cloud Messaging | Free |
| Fastlane (screenshots) | Free (CLI tool) |
| **Total** | **$99/yr + $25 once** |

Plus Apple/Google take 15-30% of subscription revenue on the native IAP
path. The web checkout (Lemon Squeezy direct) keeps 100% minus
Lemon's ~5%, so **encourage web sign-up** before promoting in-app
upgrades.

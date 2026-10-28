# Auth Test App

Minimal Android app for hand-testing SchulwareAPI sign-in, token refresh, the
mobile proxy, and web-session scraping. Everything it gets back (tokens,
`session_cookies`, web session) is kept in `SharedPreferences`.

## Build

CI builds a debug APK on every push to `test-app/**` and commits it to
[`dist/AuthTestApp-debug.apk`](dist/AuthTestApp-debug.apk).
`adb install dist/AuthTestApp-debug.apk` and you're done.

Locally (needs Android SDK + Java 17 or 21):

```sh
cd test-app
./gradlew assembleDebug
# APK at app/build/outputs/apk/debug/app-debug.apk
```

## Use

Fill the **SchulwareAPI base URL**, the **Schulnetz base URL**, and, if the
server sets `SERVICE_API_KEY`, the **Service key**. Every request sends
`X-Schulnetz-Base-Url` (and `X-Service-Key` when set).

- **Auth**: *Check login method* (`GET /api/authenticate/login-method`), then
  either *Credential login* (`POST /api/authenticate/login` with email, password,
  optional TOTP) or *Browser login*, which opens `/browser/start`'s `auth_url`
  in a WebView, catches the `callback_url` redirect, and calls `/browser/complete`.
- **Refresh**: `POST /api/authenticate/refresh` with the stored `refresh_token` +
  `device_id` (some schools answer `biometric_required`), or a silent re-login
  via `/login` with the stored `session_cookies`.
- **Webscrape**: `/api/websession/scrape` and `/validate` with the web session
  from the last login (or one captured in the WebView).
- **Mobile Proxy**: `GET /api/mobile/<endpoint>` with the stored access token.

**Reset all stored state** clears everything.

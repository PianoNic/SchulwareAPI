# SchulwareAPI Tester

Minimal Android app for hand-testing the stateless `/api/authenticate/refresh`
endpoint. Tracks `context_state` round-trips in `SharedPreferences` so you can
verify the stateless contract end to end.

## Build

CI builds a debug APK on every push to `test-app/**` and commits it to
[`dist/SchulwareAPITester-debug.apk`](dist/SchulwareAPITester-debug.apk).
`adb install dist/SchulwareAPITester-debug.apk` and you're done.

Locally (needs Android SDK + Java 17):

```sh
cd test-app
./gradlew assembleDebug
# APK at app/build/outputs/apk/debug/app-debug.apk
```

## Use

1. Open the app.
2. Fill the **SchulwareAPI base URL** (default `https://schlwr.pianonic.ch`).
3. Fill the **Schulnetz base URL** of the instance you're testing.
4. (Optional) Fill email + password — only needed when no stored context_state
   exists yet OR the Microsoft SSO session has expired server-side.
5. Tap **POST /api/authenticate/refresh**. The app:
   - Sends `{schulnetz_base_url, context_state?, email?, password?}`
   - Reads the response, persists `context_state` on success
   - Renders the pretty-printed JSON in the output area
6. Tap **Forget stored context_state** to reset and test the cold-start path.

package dev.schuly.tester

import android.annotation.SuppressLint
import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.text.method.ScrollingMovementMethod
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONArray
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Test harness for SchulwareAPI's OAuth flow:
 *  1. GET  /api/authenticate/oauth/mobile/url      → auth_url + code_verifier
 *  2. Open auth_url in a WebView, let user do Microsoft SSO
 *  3. WebViewClient intercepts the redirect carrying ?code=...
 *  4. POST /api/authenticate/oauth/mobile/callback → access_token + refresh_token
 *  5. (Bonus) POST /api/authenticate/refresh       → exercise stateless refresh
 */
class MainActivity : AppCompatActivity() {

    private val scope = CoroutineScope(Dispatchers.Main + Job())

    private lateinit var apiBaseInput: EditText
    private lateinit var schulnetzBaseInput: EditText
    private lateinit var loginBtn: Button
    private lateinit var refreshBtn: Button
    private lateinit var clearBtn: Button
    private lateinit var webView: WebView
    private lateinit var output: TextView

    private val prefs by lazy { getSharedPreferences("schulware_tester", Context.MODE_PRIVATE) }
    private var pendingCodeVerifier: String? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        apiBaseInput = field("SchulwareAPI base URL", prefs.getString("api_base", "http://localhost:8001") ?: "")
        schulnetzBaseInput = field("Schulnetz base URL", prefs.getString("schulnetz_base", "https://schulnetz.bbbaden.ch") ?: "")

        loginBtn = Button(this).apply { text = "1. Login via OAuth (one-time)" }
        refreshBtn = Button(this).apply { text = "2. Refresh using stored cookies" }
        clearBtn = Button(this).apply { text = "Reset all stored state" }

        webView = WebView(this).apply {
            visibility = View.GONE
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.databaseEnabled = true
            // SSO chain crosses origins (Microsoft → Schulnetz). Without this,
            // 3rd-party cookies set inside redirects are dropped.
            CookieManager.getInstance().setAcceptCookie(true)
            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
        }

        output = TextView(this).apply {
            text = renderStored()
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }

        val scroll = ScrollView(this).apply { addView(output) }

        listOf(apiBaseInput, schulnetzBaseInput, loginBtn, refreshBtn, clearBtn, webView, scroll)
            .forEach { root.addView(it) }
        setContentView(root)

        loginBtn.setOnClickListener { startOAuth() }
        refreshBtn.setOnClickListener { performRefresh() }
        clearBtn.setOnClickListener {
            prefs.edit().clear().apply()
            output.text = "Cleared all state."
        }
    }

    // ----- OAuth login -----

    private fun startOAuth() {
        persistBaseInputs()
        output.text = "Fetching auth URL…\n"

        scope.launch {
            val apiBase = apiBaseInput.text.toString().trimEnd('/')
            val (status, body) = withContext(Dispatchers.IO) {
                httpGet("$apiBase/api/authenticate/oauth/mobile/url")
            }
            if (status != 200) {
                output.text = "Failed to get auth URL (HTTP $status):\n$body"
                return@launch
            }
            val obj = JSONObject(body)
            val authUrl = obj.getString("authorization_url")
            pendingCodeVerifier = obj.getString("code_verifier")
            output.append("Opening auth URL in WebView. Sign in to Schulnetz/Microsoft.\n")
            openInWebView(authUrl)
        }
    }

    // origin (scheme://host) → JSON array of {name,value} entries scraped from window.localStorage
    private val capturedLocalStorage = mutableMapOf<String, String>()

    private fun openInWebView(url: String) {
        capturedLocalStorage.clear()
        webView.visibility = View.VISIBLE
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return interceptCallback(request.url)
            }
            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                if (url != null && interceptCallback(Uri.parse(url))) view?.stopLoading()
            }
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                if (view == null || url == null) return
                val u = Uri.parse(url)
                val scheme = u.scheme ?: return
                val host = u.host ?: return
                val origin = "$scheme://$host"
                view.evaluateJavascript(
                    """(function(){var o=[];try{for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);o.push({name:k,value:localStorage.getItem(k)});}}catch(e){}return JSON.stringify(o);})()"""
                ) { rawJsResult ->
                    // evaluateJavascript returns a JSON-encoded JS string: e.g. "\"[{...}]\""
                    try {
                        val unwrapped = JSONArray("[${rawJsResult}]").getString(0)
                        val arr = JSONArray(unwrapped)
                        if (arr.length() > 0) capturedLocalStorage[origin] = unwrapped
                    } catch (_: Exception) { /* ignore — origin had no localStorage */ }
                }
            }
        }
        webView.loadUrl(url)
    }

    /** Returns true if the URL was the FINAL Schulnetz callback we consumed.
     *
     * Microsoft also redirects back to Schulnetz with a `code=` query param
     * (a long MS auth code that Schulnetz consumes internally). Only the
     * **subsequent** Schulnetz-issued code at `schulnetz.web.app/callback`
     * is the one we exchange for tokens. Match strictly on that host to
     * avoid grabbing the intermediate MS code.
     *
     * On match we ALSO snapshot the WebView's cookies as a Playwright
     * `storage_state` blob — that's the context_state /refresh replays. */
    private fun interceptCallback(uri: Uri): Boolean {
        val code = uri.getQueryParameter("code") ?: return false
        if (uri.host != "schulnetz.web.app") return false
        val state = uri.getQueryParameter("state")
        captureCookiesAsContextState()
        webView.visibility = View.GONE
        exchangeCode(code, state)
        return true
    }

    /** Snapshot WebView cookies for the SSO chain into Playwright storage_state form
     * and persist them. /refresh replays them server-side; Schulnetz re-auto-logs-in
     * via Microsoft, issues a fresh code, exchanges for fresh tokens — all without
     * any user prompt. */
    private fun captureCookiesAsContextState() {
        val cm = CookieManager.getInstance().apply { flush() }
        // Stash the WebView's UA so /refresh can replay with the same string.
        prefs.edit().putString("user_agent", webView.settings.userAgentString).apply()

        // Query every plausible origin the SSO chain touches. Android exposes no
        // "list all cookies" API — getCookie(url) only returns cookies that would
        // be sent for THAT url. So we union over a wide set of plausible hosts.
        val originsToCheck = listOf(
            "https://schulnetz.bbbaden.ch",
            "https://schulnetz.web.app",
            "https://login.microsoftonline.com",
            "https://login.microsoft.com",
            "https://login.live.com",
            "https://login.windows.net",
            "https://account.live.com",
            "https://account.microsoft.com",
            "https://aadcdn.msauth.net",
            "https://aadcdn.msftauth.net",
            "https://device.login.microsoftonline.com",
            // also probe origins where we observed localStorage during the flow
        ) + capturedLocalStorage.keys

        val cookies = JSONArray()
        val seen = mutableSetOf<String>()  // dedupe (domain|name|value)
        for (origin in originsToCheck.distinct()) {
            val raw = cm.getCookie(origin) ?: continue
            val host = Uri.parse(origin).host ?: continue
            val cookieDomain = if (host.startsWith(".")) host else ".$host"
            raw.split(";").forEach { pair ->
                val parts = pair.trim().split("=", limit = 2)
                if (parts.size != 2 || parts[0].isEmpty()) return@forEach
                val key = "$cookieDomain|${parts[0]}|${parts[1]}"
                if (!seen.add(key)) return@forEach
                cookies.put(JSONObject().apply {
                    put("name", parts[0])
                    put("value", parts[1])
                    put("domain", cookieDomain)
                    put("path", "/")
                })
            }
        }

        // Emit every captured origin's localStorage into the storage_state.origins array.
        val origins = JSONArray()
        for ((origin, lsJson) in capturedLocalStorage) {
            try {
                origins.put(JSONObject().apply {
                    put("origin", origin)
                    put("localStorage", JSONArray(lsJson))
                })
            } catch (_: Exception) { /* skip malformed */ }
        }

        val storageState = JSONObject().apply {
            put("cookies", cookies)
            put("origins", origins)
        }
        prefs.edit().putString("context_state", storageState.toString()).apply()
    }

    private fun exchangeCode(code: String, state: String?) {
        val verifier = pendingCodeVerifier
        if (verifier == null) {
            output.append("\nGot code but no code_verifier stored — re-run login.")
            return
        }
        output.append("\nGot authorization code (${code.take(8)}…). Exchanging for tokens…\n")
        val apiBase = apiBaseInput.text.toString().trimEnd('/')

        scope.launch {
            val payload = JSONObject().apply {
                put("code", code)
                put("code_verifier", verifier)
                if (state != null) put("state", state)
            }
            val (status, body) = withContext(Dispatchers.IO) {
                httpPost("$apiBase/api/authenticate/oauth/mobile/callback", payload.toString())
            }
            val sb = StringBuilder()
            sb.append("HTTP ").append(status).append("\n")
            try {
                val resp = JSONObject(body)
                resp.optString("access_token", null)?.takeIf { it.isNotEmpty() }?.let {
                    prefs.edit().putString("access_token", it).apply()
                }
                resp.optString("refresh_token", null)?.takeIf { it.isNotEmpty() }?.let {
                    prefs.edit().putString("refresh_token", it).apply()
                }
                sb.append(resp.toString(2))
            } catch (_: Exception) {
                sb.append(body)
            }
            sb.append("\n\n").append(renderStored())
            output.text = sb
            pendingCodeVerifier = null
        }
    }

    // ----- Stateless /refresh test -----

    private fun performRefresh() {
        persistBaseInputs()
        val apiBase = apiBaseInput.text.toString().trimEnd('/')
        val schulnetzBase = schulnetzBaseInput.text.toString().trimEnd('/')
        output.text = "POST $apiBase/api/authenticate/refresh\n"

        scope.launch {
            val payload = JSONObject().apply {
                put("schulnetz_base_url", schulnetzBase)
                prefs.getString("context_state", null)?.let { put("context_state", JSONObject(it)) }
                // MS binds session cookies to UA — replay with the same UA the WebView used.
                prefs.getString("user_agent", null)?.let { put("user_agent", it) }
            }
            val (status, body) = withContext(Dispatchers.IO) {
                httpPost("$apiBase/api/authenticate/refresh", payload.toString())
            }
            val sb = StringBuilder()
            sb.append("HTTP ").append(status).append("\n\n")
            try {
                val obj = JSONObject(body)
                obj.optJSONObject("context_state")?.let {
                    prefs.edit().putString("context_state", it.toString()).apply()
                    sb.append("✓ context_state persisted (").append(it.toString().length).append(" chars)\n\n")
                }
                sb.append(obj.toString(2))
            } catch (_: Exception) {
                sb.append(body)
            }
            output.text = sb
        }
    }

    // ----- HTTP helpers -----

    private fun httpGet(url: String): Pair<Int, String> = runCatching {
        val con = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 15_000
            readTimeout = 60_000
            setRequestProperty("Accept", "application/json")
        }
        try {
            val status = con.responseCode
            val text = (if (status in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            status to text
        } finally { con.disconnect() }
    }.getOrElse { -1 to "Request failed: ${it.message}" }

    private fun httpPost(url: String, json: String): Pair<Int, String> = runCatching {
        val con = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = 15_000
            readTimeout = 120_000
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        try {
            con.outputStream.use { it.write(json.toByteArray()) }
            val status = con.responseCode
            val text = (if (status in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            status to text
        } finally { con.disconnect() }
    }.getOrElse { -1 to "Request failed: ${it.message}" }

    // ----- UI helpers -----

    private fun field(label: String, initial: String, password: Boolean = false): EditText = EditText(this).apply {
        hint = label
        setText(initial)
        if (password) {
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
    }

    private fun persistBaseInputs() {
        prefs.edit()
            .putString("api_base", apiBaseInput.text.toString())
            .putString("schulnetz_base", schulnetzBaseInput.text.toString())
            .apply()
    }

    private fun renderStored(): String {
        val at = prefs.getString("access_token", null)
        val rt = prefs.getString("refresh_token", null)
        val cs = prefs.getString("context_state", null)
        return buildString {
            append("Stored:\n")
            append("  access_token:  ").append(if (at != null) "${at.take(12)}… (${at.length})" else "—").append('\n')
            append("  refresh_token: ").append(if (rt != null) "${rt.take(12)}… (${rt.length})" else "—").append('\n')
            append("  context_state: ").append(if (cs != null) "${cs.length} chars" else "—").append('\n')
        }
    }
}

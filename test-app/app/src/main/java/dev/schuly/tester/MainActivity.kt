package dev.schuly.tester

import android.annotation.SuppressLint
import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.text.method.ScrollingMovementMethod
import android.view.View
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
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

        apiBaseInput = field("SchulwareAPI base URL", prefs.getString("api_base", "http://localhost:8000") ?: "")
        schulnetzBaseInput = field("Schulnetz base URL (for refresh)", prefs.getString("schulnetz_base", "https://schulnetz.bbbaden.ch") ?: "")

        loginBtn = Button(this).apply { text = "1. Login via OAuth" }
        refreshBtn = Button(this).apply { text = "2. Test stateless refresh" }
        clearBtn = Button(this).apply { text = "Reset all stored state" }

        webView = WebView(this).apply {
            visibility = View.GONE
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
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

    private fun openInWebView(url: String) {
        webView.visibility = View.VISIBLE
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return interceptCallback(request.url)
            }
            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                if (url != null && interceptCallback(Uri.parse(url))) view?.stopLoading()
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
     * avoid grabbing the intermediate MS code. */
    private fun interceptCallback(uri: Uri): Boolean {
        val code = uri.getQueryParameter("code") ?: return false
        if (uri.host != "schulnetz.web.app") return false
        val state = uri.getQueryParameter("state")
        webView.visibility = View.GONE
        exchangeCode(code, state)
        return true
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

    private fun field(label: String, initial: String): EditText = EditText(this).apply {
        hint = label
        setText(initial)
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

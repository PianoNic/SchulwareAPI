package dev.schuly.tester

import android.annotation.SuppressLint
import android.net.Uri
import android.text.method.ScrollingMovementMethod
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * Tab 1: Mobile OAuth login.
 *
 *  1. GET  /api/authenticate/oauth/mobile/url      → auth_url + code_verifier
 *  2. Open auth_url in a WebView, let user do Microsoft SSO
 *  3. WebViewClient intercepts the redirect carrying ?code=...
 *  4. POST /api/authenticate/oauth/mobile/callback → access_token + refresh_token
 *
 * Also snapshots the WebView's cookies + localStorage as a Playwright
 * `storage_state` blob (the `context_state` that the Refresh tab replays).
 */
class AuthTab : TabSection {

    private lateinit var output: TextView
    private var pendingCodeVerifier: String? = null
    // origin (scheme://host) → JSON array of {name,value} entries scraped from window.localStorage
    private val capturedLocalStorage = mutableMapOf<String, String>()

    @SuppressLint("SetJavaScriptEnabled")
    override fun build(ctx: TabContext): View {
        val root = LinearLayout(ctx.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 0)
        }

        val loginBtn = Button(ctx.activity).apply { text = "Login via OAuth (one-time)" }

        output = TextView(ctx.activity).apply {
            text = renderStored(ctx)
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }
        val scroll = ScrollView(ctx.activity).apply { addView(output) }

        root.addView(loginBtn)
        root.addView(scroll)

        loginBtn.setOnClickListener { startOAuth(ctx) }
        return root
    }

    private fun startOAuth(ctx: TabContext) {
        output.text = "Fetching auth URL…\n"
        ctx.scope.launch {
            val apiBase = ctx.getApiBase()
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpGet("$apiBase/api/authenticate/oauth/mobile/url")
            }
            if (status != 200) {
                output.text = "Failed to get auth URL (HTTP $status):\n$body"
                return@launch
            }
            val obj = JSONObject(body)
            val authUrl = obj.getString("authorization_url")
            pendingCodeVerifier = obj.getString("code_verifier")
            output.append("Opening auth URL in WebView. Sign in to Schulnetz/Microsoft.\n")
            openInWebView(ctx, authUrl)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun openInWebView(ctx: TabContext, url: String) {
        capturedLocalStorage.clear()
        val webView = ctx.sharedWebView
        webView.visibility = View.VISIBLE
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                return interceptCallback(ctx, request.url)
            }
            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                if (url != null && interceptCallback(ctx, Uri.parse(url))) view?.stopLoading()
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

    /** True iff this was the FINAL Schulnetz callback (not the intermediate MS code). */
    private fun interceptCallback(ctx: TabContext, uri: Uri): Boolean {
        val code = uri.getQueryParameter("code") ?: return false
        if (uri.host != "schulnetz.web.app") return false
        val state = uri.getQueryParameter("state")
        captureCookiesAsContextState(ctx)
        ctx.sharedWebView.visibility = View.GONE
        exchangeCode(ctx, code, state)
        return true
    }

    private fun captureCookiesAsContextState(ctx: TabContext) {
        val cm = CookieManager.getInstance().apply { flush() }
        ctx.prefs.edit().putString("user_agent", ctx.sharedWebView.settings.userAgentString).apply()

        val originsToCheck = listOf(
            ctx.getSchulnetzBase(),
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
        ) + capturedLocalStorage.keys

        val cookies = JSONArray()
        val seen = mutableSetOf<String>()
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
        ctx.prefs.edit().putString("context_state", storageState.toString()).apply()
    }

    private fun exchangeCode(ctx: TabContext, code: String, state: String?) {
        val verifier = pendingCodeVerifier
        if (verifier == null) {
            output.append("\nGot code but no code_verifier stored — re-run login.")
            return
        }
        output.append("\nGot authorization code (${code.take(8)}…). Exchanging for tokens…\n")
        val apiBase = ctx.getApiBase()

        ctx.scope.launch {
            val payload = JSONObject().apply {
                put("code", code)
                put("code_verifier", verifier)
                if (state != null) put("state", state)
            }
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpPost("$apiBase/api/authenticate/oauth/mobile/callback", payload.toString())
            }
            val sb = StringBuilder()
            sb.append("HTTP ").append(status).append("\n")
            try {
                val resp = JSONObject(body)
                resp.optString("access_token", null)?.takeIf { it.isNotEmpty() }?.let {
                    ctx.prefs.edit().putString("access_token", it).apply()
                }
                resp.optString("refresh_token", null)?.takeIf { it.isNotEmpty() }?.let {
                    ctx.prefs.edit().putString("refresh_token", it).apply()
                }
                sb.append(resp.toString(2))
            } catch (_: Exception) {
                sb.append(body)
            }
            sb.append("\n\n").append(renderStored(ctx))
            output.text = sb
            pendingCodeVerifier = null
        }
    }

    private fun renderStored(ctx: TabContext): String {
        val at = ctx.prefs.getString("access_token", null)
        val rt = ctx.prefs.getString("refresh_token", null)
        val cs = ctx.prefs.getString("context_state", null)
        return buildString {
            append("Stored:\n")
            append("  access_token:  ").append(if (at != null) "${at.take(12)}… (${at.length})" else "—").append('\n')
            append("  refresh_token: ").append(if (rt != null) "${rt.take(12)}… (${rt.length})" else "—").append('\n')
            append("  context_state: ").append(if (cs != null) "${cs.length} chars" else "—").append('\n')
        }
    }
}

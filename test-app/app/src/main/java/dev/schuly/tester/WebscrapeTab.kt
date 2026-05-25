package dev.schuly.tester

import android.annotation.SuppressLint
import android.text.method.ScrollingMovementMethod
import android.view.View
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Tab 3: Web session — exercise the /api/websession/... endpoints.
 *
 * Architecture note: the OAuth code Schulnetz issues is bound to the BROWSER's
 * Microsoft session cookies, so it can ONLY be redeemed by the WebView itself.
 * Server-side code exchange returns a PHPSESSID for an UNauthenticated session
 * (we tested this — the response is the "session expired" page). So the test
 * app extracts the session material directly from the WebView once login
 * completes, then sends those to /scrape and /validate.
 *
 *  1. Open `{schulnetzBase}/` in a WebView. Schulnetz redirects through MS SSO
 *     and ultimately lands on `{schulnetzBase}/loginto.php?mode=4&lang=` (the
 *     dashboard). At that point the WebView's cookie jar has a real PHPSESSID
 *     and the page's nav links contain `id` and `transid`.
 *  2. Extract session_id (PHPSESSID), id, transid from the WebView.
 *  3. POST /api/websession/scrape    { session_id, id, transid, page }
 *  4. POST /api/websession/validate  { session_id, id, transid }
 */
class WebscrapeTab : TabSection {

    private lateinit var output: TextView
    private lateinit var pageSpinner: Spinner

    private val pages = listOf(
        "home", "grades", "absences", "agenda",
        "lessons", "documents", "student_id", "schedule",
    )

    @SuppressLint("SetJavaScriptEnabled")
    override fun build(ctx: TabContext): View {
        val root = LinearLayout(ctx.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 0)
        }

        val captureBtn = Button(ctx.activity).apply { text = "1. Login via Web OAuth (one-time)" }

        pageSpinner = Spinner(ctx.activity).apply {
            adapter = ArrayAdapter(ctx.activity, android.R.layout.simple_spinner_dropdown_item, pages)
        }
        val scrapeBtn = Button(ctx.activity).apply { text = "2. Scrape selected page" }
        val validateBtn = Button(ctx.activity).apply { text = "3. Validate session" }

        output = TextView(ctx.activity).apply {
            text = renderStored(ctx)
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }
        val scroll = ScrollView(ctx.activity).apply { addView(output) }

        listOf<View>(captureBtn, pageSpinner, scrapeBtn, validateBtn, scroll).forEach { root.addView(it) }

        captureBtn.setOnClickListener { startWebLogin(ctx) }
        scrapeBtn.setOnClickListener { performScrape(ctx) }
        validateBtn.setOnClickListener { performValidate(ctx) }
        return root
    }

    // ----- WebView login + client-side session extraction -----

    @SuppressLint("SetJavaScriptEnabled")
    private fun startWebLogin(ctx: TabContext) {
        val schulnetzBase = ctx.getSchulnetzBase()
        val schulnetzHost = android.net.Uri.parse(schulnetzBase).host ?: ""
        output.text = "Opening $schulnetzBase in WebView. Schulnetz will redirect through MS SSO.\n" +
                "Waiting for the dashboard to load…\n"

        val webView = ctx.sharedWebView
        var extracted = false  // guard so we only capture once per login
        webView.visibility = View.VISIBLE
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                if (extracted || view == null || url == null) return
                val host = android.net.Uri.parse(url).host ?: return
                // Only consider pages on the schulnetz host (skip MS SSO hops).
                if (host != schulnetzHost) return
                // Surface the URL so a debugger can see where we are.
                output.append("\nonPageFinished: $url\n")
                extractSession(ctx, view, url) { ok ->
                    if (ok) extracted = true
                }
            }
        }
        webView.loadUrl(schulnetzBase)
    }

    /** Pulls PHPSESSID from CookieManager and id/transid from any pageid link in the rendered page. */
    private fun extractSession(ctx: TabContext, view: WebView, url: String, done: (Boolean) -> Unit) {
        val schulnetzBase = ctx.getSchulnetzBase()
        // CookieManager.getCookie returns even HttpOnly cookies (unlike document.cookie).
        val raw = CookieManager.getInstance().getCookie(schulnetzBase) ?: ""
        val sessionId = raw.split(";")
            .map { it.trim() }
            .firstOrNull { it.startsWith("PHPSESSID=") }
            ?.substringAfter("=")
        if (sessionId.isNullOrEmpty()) {
            output.append("\nNo PHPSESSID cookie yet — page still loading?\n")
            done(false)
            return
        }

        // Grab id+transid from the first nav link on the dashboard.
        view.evaluateJavascript(
            """(function(){
                var a = document.querySelector('a[href*="pageid"]');
                if (!a) return JSON.stringify(null);
                var href = a.getAttribute('href') || '';
                var id = (href.match(/[?&]id=([a-f0-9]+)/) || [])[1];
                var transid = (href.match(/[?&]transid=([a-f0-9]+)/) || [])[1];
                return JSON.stringify({id: id || null, transid: transid || null});
            })()""".trimIndent(),
        ) { rawResult ->
            val parsed = try {
                val unwrapped = rawResult?.removePrefix("\"")?.removeSuffix("\"")
                    ?.replace("\\\"", "\"")
                if (unwrapped == "null" || unwrapped.isNullOrEmpty()) null
                else JSONObject(unwrapped)
            } catch (_: Exception) { null }

            val id = parsed?.optString("id", "")?.takeUnless { it.isEmpty() }
            val transid = parsed?.optString("transid", "")?.takeUnless { it.isEmpty() }

            if (id == null || transid == null) {
                output.append("\nGot PHPSESSID but no id/transid links yet — page may still be loading.\n")
                done(false)
                return@evaluateJavascript
            }

            ctx.prefs.edit()
                .putString("web_session_id", sessionId)
                .putString("web_id", id)
                .putString("web_transid", transid)
                // Schulnetz binds PHPSESSID to the UA that created it — replay
                // server-side with the same UA or the session is rejected.
                .putString("web_user_agent", view.settings.userAgentString)
                .apply()

            ctx.sharedWebView.visibility = View.GONE
            output.text = buildString {
                append("✓ Web session captured.\n\n")
                append(renderStored(ctx))
            }
            done(true)
        }
    }

    // ----- /websession/scrape -----

    private fun performScrape(ctx: TabContext) {
        val sid = ctx.prefs.getString("web_session_id", null)
        val id = ctx.prefs.getString("web_id", null)
        val transid = ctx.prefs.getString("web_transid", null)
        if (sid == null || id == null || transid == null) {
            output.text = "No web session stored. Run step 1 first."
            return
        }
        val page = pageSpinner.selectedItem as String
        val ua = ctx.prefs.getString("web_user_agent", null)
        val apiBase = ctx.getApiBase()
        output.text = "POST $apiBase/api/websession/scrape (page=$page)\n"
        ctx.scope.launch {
            val payload = JSONObject().apply {
                put("session_id", sid)
                put("id", id)
                put("transid", transid)
                put("page", page)
                if (ua != null) put("user_agent", ua)
            }
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpPost("$apiBase/api/websession/scrape", payload.toString())
            }
            renderJson(status, body)
        }
    }

    // ----- /websession/validate -----

    private fun performValidate(ctx: TabContext) {
        val sid = ctx.prefs.getString("web_session_id", null)
        val id = ctx.prefs.getString("web_id", null)
        val transid = ctx.prefs.getString("web_transid", null)
        if (sid == null || id == null || transid == null) {
            output.text = "No web session stored. Run step 1 first."
            return
        }
        val ua = ctx.prefs.getString("web_user_agent", null)
        val apiBase = ctx.getApiBase()
        output.text = "POST $apiBase/api/websession/validate\n"
        ctx.scope.launch {
            val payload = JSONObject().apply {
                put("session_id", sid)
                put("id", id)
                put("transid", transid)
                put("page", "home") // ignored by handler but DTO requires it
                if (ua != null) put("user_agent", ua)
            }
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpPost("$apiBase/api/websession/validate", payload.toString())
            }
            renderJson(status, body)
        }
    }

    private fun renderJson(status: Int, body: String) {
        val sb = StringBuilder()
        sb.append("HTTP ").append(status).append("\n\n")
        try {
            sb.append(JSONObject(body).toString(2))
        } catch (_: Exception) {
            sb.append(body)
        }
        output.text = sb
    }

    private fun renderStored(ctx: TabContext): String {
        val sid = ctx.prefs.getString("web_session_id", null)
        val id = ctx.prefs.getString("web_id", null)
        val transid = ctx.prefs.getString("web_transid", null)
        return buildString {
            append("Stored web session:\n")
            append("  PHPSESSID: ").append(if (sid != null) "${sid.take(12)}… (${sid.length})" else "—").append('\n')
            append("  id:        ").append(id ?: "—").append('\n')
            append("  transid:   ").append(transid ?: "—").append('\n')
        }
    }
}

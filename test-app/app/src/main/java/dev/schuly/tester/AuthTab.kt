package dev.schuly.tester

import android.annotation.SuppressLint
import android.net.Uri
import android.text.InputType
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Tab 1: Sign-in.
 *
 *  - GET  /api/authenticate/login-method   → microsoft | native | browser
 *  - POST /api/authenticate/login          → credential login (email, password, TOTP)
 *  - POST /api/authenticate/browser/start  → auth_url opened in the WebView;
 *    the callback carrying `code` + `state` is intercepted and sent to
 *    POST /api/authenticate/browser/complete
 */
class AuthTab : TabSection {

    private lateinit var output: TextView
    private lateinit var email: EditText
    private lateinit var password: EditText
    private lateinit var totpSecret: EditText
    private lateinit var totpCode: EditText

    override fun build(ctx: TabContext): View {
        val root = LinearLayout(ctx.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 0)
        }

        email = EditText(ctx.activity).apply {
            hint = "Email"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
        }
        password = EditText(ctx.activity).apply {
            hint = "Password"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        totpSecret = EditText(ctx.activity).apply { hint = "TOTP secret (optional)" }
        totpCode = EditText(ctx.activity).apply {
            hint = "TOTP code (optional)"
            inputType = InputType.TYPE_CLASS_NUMBER
        }
        val methodBtn = Button(ctx.activity).apply { text = "Check login method" }
        val loginBtn = Button(ctx.activity).apply { text = "Credential login" }
        val browserBtn = Button(ctx.activity).apply { text = "Browser login (WebView)" }

        output = TextView(ctx.activity).apply {
            text = ctx.renderStored()
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }
        val scroll = ScrollView(ctx.activity).apply { addView(output) }

        listOf<View>(methodBtn, email, password, totpSecret, totpCode, loginBtn, browserBtn, scroll).forEach { root.addView(it) }

        methodBtn.setOnClickListener { checkMethod(ctx) }
        loginBtn.setOnClickListener { credentialLogin(ctx) }
        browserBtn.setOnClickListener { startBrowserLogin(ctx) }
        return root
    }

    private fun checkMethod(ctx: TabContext) {
        val url = "${ctx.getApiBase()}/api/authenticate/login-method"
        output.text = "GET $url\n"
        ctx.scope.launch {
            val (status, body) = withContext(Dispatchers.IO) { Net.httpGet(url, headers = ctx.headers()) }
            output.text = "HTTP $status\n\n${prettyJson(body)}"
        }
    }

    private fun credentialLogin(ctx: TabContext) {
        val payload = JSONObject().apply {
            put("schulnetz_base_url", ctx.getSchulnetzBase())
            put("email", email.text.toString())
            put("password", password.text.toString())
            totpSecret.text.toString().takeIf { it.isNotBlank() }?.let { put("totp_secret", it.trim()) }
            totpCode.text.toString().takeIf { it.isNotBlank() }?.let { put("totp_code", it.trim()) }
        }
        post(ctx, "/api/authenticate/login", payload)
    }

    private fun startBrowserLogin(ctx: TabContext) {
        val apiBase = ctx.getApiBase()
        output.text = "POST $apiBase/api/authenticate/browser/start\n"
        ctx.scope.launch {
            val payload = JSONObject().put("schulnetz_base_url", ctx.getSchulnetzBase())
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpPost("$apiBase/api/authenticate/browser/start", payload.toString(), headers = ctx.headers())
            }
            if (status != 200) {
                output.text = "HTTP $status\n\n${prettyJson(body)}"
                return@launch
            }
            val start = JSONObject(body)
            ctx.prefs.edit().putString("device_id", start.getString("device_id")).apply()
            output.append("Sign in inside the WebView.\n")
            openInWebView(ctx, start)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun openInWebView(ctx: TabContext, start: JSONObject) {
        val callbackUrl = start.getString("callback_url")
        val state = start.getString("state")
        var done = false
        fun intercept(uri: Uri): Boolean {
            if (done || !uri.toString().startsWith(callbackUrl)) return false
            val code = uri.getQueryParameter("code") ?: return false
            if (uri.getQueryParameter("state") != state) return false
            done = true
            ctx.sharedWebView.visibility = View.GONE
            val payload = JSONObject().apply {
                put("schulnetz_base_url", ctx.getSchulnetzBase())
                put("code", code)
                put("code_verifier", start.getString("code_verifier"))
                put("device_id", start.getString("device_id"))
            }
            post(ctx, "/api/authenticate/browser/complete", payload)
            return true
        }

        val webView = ctx.sharedWebView
        webView.visibility = View.VISIBLE
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = intercept(request.url)
            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                if (url != null && intercept(Uri.parse(url))) view?.stopLoading()
            }
        }
        webView.loadUrl(start.getString("auth_url"))
    }

    private fun post(ctx: TabContext, path: String, payload: JSONObject) {
        val url = "${ctx.getApiBase()}$path"
        output.text = "POST $url\n"
        ctx.scope.launch {
            val (status, body) = withContext(Dispatchers.IO) { Net.httpPost(url, payload.toString(), headers = ctx.headers()) }
            runCatching { ctx.storeLogin(JSONObject(body)) }
            output.text = "HTTP $status\n\n${prettyJson(body)}\n\n${ctx.renderStored()}"
        }
    }
}

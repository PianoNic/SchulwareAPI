package dev.schuly.tester

import android.text.method.ScrollingMovementMethod
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * Tab 2: Token refresh and silent re-login.
 *
 *  - POST /api/authenticate/refresh  { schulnetz_base_url, refresh_token, device_id }
 *    (some schools answer `biometric_required`)
 *  - POST /api/authenticate/login    { schulnetz_base_url, session_cookies }
 */
class RefreshTab : TabSection {

    private lateinit var output: TextView

    override fun build(ctx: TabContext): View {
        val root = LinearLayout(ctx.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 0)
        }

        val refreshBtn = Button(ctx.activity).apply { text = "Refresh with refresh_token" }
        val reloginBtn = Button(ctx.activity).apply { text = "Re-login with session_cookies" }

        output = TextView(ctx.activity).apply {
            text = ctx.renderStored()
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }
        val scroll = ScrollView(ctx.activity).apply { addView(output) }

        listOf<View>(refreshBtn, reloginBtn, scroll).forEach { root.addView(it) }

        refreshBtn.setOnClickListener { performRefresh(ctx) }
        reloginBtn.setOnClickListener { performRelogin(ctx) }
        return root
    }

    private fun performRefresh(ctx: TabContext) {
        val refreshToken = ctx.prefs.getString("refresh_token", null)
        if (refreshToken == null) {
            output.text = "No refresh_token stored. Log in via the Auth tab first."
            return
        }
        val deviceId = ctx.prefs.getString("device_id", null) ?: UUID.randomUUID().toString().also {
            ctx.prefs.edit().putString("device_id", it).apply()
        }
        val payload = JSONObject().apply {
            put("schulnetz_base_url", ctx.getSchulnetzBase())
            put("refresh_token", refreshToken)
            put("device_id", deviceId)
        }
        post(ctx, "/api/authenticate/refresh", payload)
    }

    private fun performRelogin(ctx: TabContext) {
        val cookies = ctx.prefs.getString("session_cookies", null)
        if (cookies == null) {
            output.text = "No session_cookies stored. Do a credential login via the Auth tab first."
            return
        }
        val payload = JSONObject().apply {
            put("schulnetz_base_url", ctx.getSchulnetzBase())
            put("session_cookies", JSONArray(cookies))
        }
        post(ctx, "/api/authenticate/login", payload)
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

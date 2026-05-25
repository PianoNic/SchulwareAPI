package dev.schuly.tester

import android.text.method.ScrollingMovementMethod
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Tab 2: Stateless /api/authenticate/refresh.
 *
 * Replays the `context_state` captured by the Auth tab to mint a fresh set of
 * tokens server-side, then updates the persisted context_state.
 */
class RefreshTab : TabSection {

    private lateinit var output: TextView

    override fun build(ctx: TabContext): View {
        val root = LinearLayout(ctx.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 0)
        }

        val refreshBtn = Button(ctx.activity).apply { text = "Refresh using stored cookies" }

        output = TextView(ctx.activity).apply {
            text = "Tap to POST /api/authenticate/refresh with the stored context_state."
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }
        val scroll = ScrollView(ctx.activity).apply { addView(output) }

        root.addView(refreshBtn)
        root.addView(scroll)

        refreshBtn.setOnClickListener { performRefresh(ctx) }
        return root
    }

    private fun performRefresh(ctx: TabContext) {
        val apiBase = ctx.getApiBase()
        val schulnetzBase = ctx.getSchulnetzBase()
        output.text = "POST $apiBase/api/authenticate/refresh\n"

        ctx.scope.launch {
            val payload = JSONObject().apply {
                put("schulnetz_base_url", schulnetzBase)
                ctx.prefs.getString("context_state", null)?.let { put("context_state", JSONObject(it)) }
                // MS binds session cookies to UA — replay with the same UA the WebView used.
                ctx.prefs.getString("user_agent", null)?.let { put("user_agent", it) }
            }
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpPost("$apiBase/api/authenticate/refresh", payload.toString())
            }
            val sb = StringBuilder()
            sb.append("HTTP ").append(status).append("\n\n")
            try {
                val obj = JSONObject(body)
                obj.optJSONObject("context_state")?.let {
                    ctx.prefs.edit().putString("context_state", it.toString()).apply()
                    sb.append("✓ context_state persisted (").append(it.toString().length).append(" chars)\n\n")
                }
                obj.optString("access_token", null)?.takeIf { it.isNotEmpty() }?.let {
                    ctx.prefs.edit().putString("access_token", it).apply()
                }
                obj.optString("refresh_token", null)?.takeIf { it.isNotEmpty() }?.let {
                    ctx.prefs.edit().putString("refresh_token", it).apply()
                }
                sb.append(obj.toString(2))
            } catch (_: Exception) {
                sb.append(body)
            }
            output.text = sb
        }
    }
}

package dev.schuly.tester

import android.content.Context
import android.content.SharedPreferences
import android.webkit.WebView
import kotlinx.coroutines.CoroutineScope
import org.json.JSONArray
import org.json.JSONObject

/** Shared state and dependencies passed to every tab section. */
data class TabContext(
    val activity: Context,
    val prefs: SharedPreferences,
    val scope: CoroutineScope,
    val sharedWebView: WebView,
    val getApiBase: () -> String,
    val getSchulnetzBase: () -> String,
    val getServiceKey: () -> String,
) {
    /** `X-Schulnetz-Base-Url` plus `X-Service-Key` when one is set. */
    fun headers(): Map<String, String> = buildMap {
        put("X-Schulnetz-Base-Url", getSchulnetzBase())
        getServiceKey().takeIf { it.isNotEmpty() }?.let { put("X-Service-Key", it) }
    }

    /** Persists the non-empty fields of a LoginResponseDto. */
    fun storeLogin(resp: JSONObject) {
        val edit = prefs.edit()
        fun str(key: String) = resp.optString(key, "").takeIf { it.isNotEmpty() && it != "null" }
        str("access_token")?.let { edit.putString("access_token", it) }
        str("refresh_token")?.let { edit.putString("refresh_token", it) }
        resp.optJSONArray("session_cookies")?.let { edit.putString("session_cookies", it.toString()) }
        val sid = str("session_id")
        val id = str("web_session_user_id")
        val transid = str("web_session_trans_id")
        if (sid != null && id != null && transid != null) {
            edit.putString("web_session_id", sid).putString("web_id", id).putString("web_transid", transid).remove("web_user_agent")
        }
        edit.apply()
    }

    /** One-line summary of everything stored. */
    fun renderStored(): String {
        fun short(key: String) = prefs.getString(key, null)?.let { "${it.take(12)}… (${it.length})" } ?: "—"
        val cookies = prefs.getString("session_cookies", null)?.let { "${JSONArray(it).length()} cookies" } ?: "—"
        return buildString {
            append("Stored:\n")
            append("  access_token:    ").append(short("access_token")).append('\n')
            append("  refresh_token:   ").append(short("refresh_token")).append('\n')
            append("  device_id:       ").append(prefs.getString("device_id", null) ?: "—").append('\n')
            append("  session_cookies: ").append(cookies).append('\n')
            append("  web session:     ").append(short("web_session_id")).append('\n')
        }
    }
}

interface TabSection {
    /** Build and return this tab's root view. Called once at startup. */
    fun build(ctx: TabContext): android.view.View
}

/** Best-effort pretty-print: object, then array, then raw. */
fun prettyJson(body: String): String {
    if (body.isEmpty()) return ""
    return runCatching { JSONObject(body).toString(2) }
        .recoverCatching { JSONArray(body).toString(2) }
        .getOrElse { body }
}

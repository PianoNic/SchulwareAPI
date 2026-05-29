package dev.schuly.tester

import android.text.method.ScrollingMovementMethod
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * Tab 4: Mobile proxy — exercise the /api/mobile/... endpoints with the stored access_token as a Bearer.
 *
 * The dropdown lists every GET endpoint the proxy exposes. /events and /agenda
 * accept optional min_date/max_date query params; we send neither (server treats
 * them as None). /studentidcard takes a report_id path param; we hardcode `1`.
 */
class ProxyTab : TabSection {

    private lateinit var output: TextView
    private lateinit var endpointSpinner: Spinner

    /** (display label, path under /api/mobile/) */
    private val endpoints = listOf(
        "userInfo"                to "userInfo",
        "grades"                  to "grades",
        "events"                  to "events",
        "agenda"                  to "agenda",
        "exams"                   to "exams",
        "absences"                to "absences",
        "absencenotices"          to "absencenotices",
        "absencenoticestatus"     to "absencenoticestatus",
        "absences/confirmed"      to "absences/confirmed",
        "lateness"                to "lateness",
        "vacations"               to "vacations",
        "homework"                to "homework",
        "objectives"              to "objectives",
        "notifications"           to "notifications",
        "topics"                  to "topics",
        "settings"                to "settings",
        "customfields"            to "customfields",
        "filecategories"          to "filecategories",
        "studentidcard/1"         to "studentidcard/1",
    )

    override fun build(ctx: TabContext): View {
        val root = LinearLayout(ctx.activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 16, 0, 0)
        }

        endpointSpinner = Spinner(ctx.activity).apply {
            adapter = ArrayAdapter(
                ctx.activity,
                android.R.layout.simple_spinner_dropdown_item,
                endpoints.map { it.first },
            )
        }
        val getBtn = Button(ctx.activity).apply { text = "GET selected endpoint" }

        output = TextView(ctx.activity).apply {
            text = "Authorization: Bearer <access_token from Auth tab>"
            setPadding(0, 32, 0, 0)
            movementMethod = ScrollingMovementMethod()
        }
        val scroll = ScrollView(ctx.activity).apply { addView(output) }

        listOf<View>(endpointSpinner, getBtn, scroll).forEach { root.addView(it) }
        getBtn.setOnClickListener { performGet(ctx) }
        return root
    }

    private fun performGet(ctx: TabContext) {
        val token = ctx.prefs.getString("access_token", null)
        if (token.isNullOrEmpty()) {
            output.text = "No access_token stored. Log in via the Auth tab first."
            return
        }
        val path = endpoints[endpointSpinner.selectedItemPosition].second
        val apiBase = ctx.getApiBase()
        val schulnetzBase = ctx.getSchulnetzBase()
        val url = "$apiBase/api/mobile/$path"
        output.text = "GET $url\nX-Schulnetz-Base-Url: $schulnetzBase\n"

        ctx.scope.launch {
            val (status, body) = withContext(Dispatchers.IO) {
                Net.httpGet(url, bearer = token, headers = mapOf("X-Schulnetz-Base-Url" to schulnetzBase))
            }
            val sb = StringBuilder()
            sb.append("HTTP ").append(status).append("\n\n")
            sb.append(prettyJson(body))
            output.text = sb
        }
    }

    /** Best-effort pretty-print: tries object, then array, then falls back to raw. */
    private fun prettyJson(body: String): String {
        if (body.isEmpty()) return ""
        return runCatching { JSONObject(body).toString(2) }
            .recoverCatching { JSONArray(body).toString(2) }
            .getOrElse { body }
    }
}

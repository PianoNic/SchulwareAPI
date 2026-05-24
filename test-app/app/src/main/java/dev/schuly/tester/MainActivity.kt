package dev.schuly.tester

import android.content.Context
import android.os.Bundle
import android.text.method.ScrollingMovementMethod
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
 * Minimal harness that calls SchulwareAPI's stateless /api/authenticate/refresh.
 *
 * Persists the returned context_state in SharedPreferences so subsequent calls
 * round-trip it back — proving the stateless contract end to end.
 */
class MainActivity : AppCompatActivity() {

    private val scope = CoroutineScope(Dispatchers.Main + Job())

    private lateinit var apiBaseInput: EditText
    private lateinit var schulnetzBaseInput: EditText
    private lateinit var emailInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var output: TextView

    private val prefs by lazy { getSharedPreferences("schulware_tester", Context.MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        apiBaseInput = labeledField("SchulwareAPI base URL", prefs.getString("api_base", "https://schlwr.pianonic.ch") ?: "")
        schulnetzBaseInput = labeledField("Schulnetz base URL", prefs.getString("schulnetz_base", "") ?: "")
        emailInput = labeledField("Email (only if SSO needed)", prefs.getString("email", "") ?: "")
        passwordInput = labeledField("Password (only if SSO needed)", "", password = true)

        val refreshBtn = Button(this).apply { text = "POST /api/authenticate/refresh" }
        val clearBtn = Button(this).apply { text = "Forget stored context_state" }

        output = TextView(this).apply {
            text = "Ready. Stored context_state: ${if (prefs.contains("context_state")) "yes (${prefs.getString("context_state","")!!.length} chars)" else "none"}"
            setPadding(0, 32, 0, 0)
            setHorizontallyScrolling(true)
            movementMethod = ScrollingMovementMethod()
        }

        val scroll = ScrollView(this).apply { addView(output) }

        listOf(apiBaseInput, schulnetzBaseInput, emailInput, passwordInput, refreshBtn, clearBtn, scroll)
            .forEach { root.addView(it) }

        setContentView(root)

        refreshBtn.setOnClickListener { performRefresh() }
        clearBtn.setOnClickListener {
            prefs.edit().remove("context_state").apply()
            output.text = "Cleared stored context_state."
        }
    }

    private fun labeledField(label: String, initial: String, password: Boolean = false): EditText {
        val v = EditText(this).apply {
            hint = label
            setText(initial)
            if (password) {
                inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
            }
        }
        return v
    }

    private fun performRefresh() {
        val apiBase = apiBaseInput.text.toString().trimEnd('/')
        val schulnetzBase = schulnetzBaseInput.text.toString().trimEnd('/')
        val email = emailInput.text.toString().trim()
        val password = passwordInput.text.toString()

        prefs.edit()
            .putString("api_base", apiBase)
            .putString("schulnetz_base", schulnetzBase)
            .putString("email", email)
            .apply()

        output.text = "Calling $apiBase/api/authenticate/refresh ...\n"

        scope.launch {
            val (status, body) = withContext(Dispatchers.IO) { callRefresh(apiBase, schulnetzBase, email, password) }
            renderResult(status, body)
        }
    }

    private fun callRefresh(apiBase: String, schulnetzBase: String, email: String, password: String): Pair<Int, String> {
        val payload = JSONObject().apply {
            put("schulnetz_base_url", schulnetzBase)
            prefs.getString("context_state", null)?.let { put("context_state", JSONObject(it)) }
            if (email.isNotEmpty()) put("email", email)
            if (password.isNotEmpty()) put("password", password)
        }
        val url = URL("$apiBase/api/authenticate/refresh")
        val con = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = 15_000
            readTimeout = 120_000
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }
        return try {
            con.outputStream.use { it.write(payload.toString().toByteArray()) }
            val status = con.responseCode
            val text = (if (status in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            status to text
        } catch (e: Exception) {
            -1 to "Request failed: ${e.message}"
        } finally {
            con.disconnect()
        }
    }

    private fun renderResult(status: Int, body: String) {
        val sb = StringBuilder()
        sb.append("HTTP ").append(status).append("\n\n")
        try {
            val obj = JSONObject(body)
            // Persist context_state if returned.
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

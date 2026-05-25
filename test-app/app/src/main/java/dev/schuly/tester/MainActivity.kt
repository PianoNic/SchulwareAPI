package dev.schuly.tester

import android.annotation.SuppressLint
import android.content.Context
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebView
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.tabs.TabLayout
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job

/**
 * SchulwareAPI Auth Test App — tabbed harness.
 *
 *  Tab 1 – Auth:        OAuth login → access/refresh tokens + context_state
 *  Tab 2 – Refresh:     stateless /refresh using stored context_state
 *  Tab 3 – Webscrape:   web OAuth → capture → scrape / validate
 *  Tab 4 – Mobile Proxy: GET each /api/mobile/... endpoint with the access_token
 *
 * Tabs share: the API + Schulnetz base URL inputs (header), a single WebView
 * (so SSO state carries across flows), and SharedPreferences for all
 * persisted tokens/cookies.
 */
class MainActivity : AppCompatActivity() {

    private val scope = CoroutineScope(Dispatchers.Main + Job())
    private val prefs by lazy { getSharedPreferences("schulware_tester", Context.MODE_PRIVATE) }

    private lateinit var apiBaseInput: EditText
    private lateinit var schulnetzBaseInput: EditText
    private lateinit var sharedWebView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        // ---- shared header: base URL inputs + reset button ----
        apiBaseInput = field("SchulwareAPI base URL", prefs.getString("api_base", "http://localhost:8000") ?: "")
        schulnetzBaseInput = field("Schulnetz base URL", prefs.getString("schulnetz_base", "https://schulnetz.bbbaden.ch") ?: "")
        val clearBtn = Button(this).apply { text = "Reset all stored state" }

        // ---- shared WebView (hidden by default; tabs flip it visible during OAuth) ----
        sharedWebView = WebView(this).apply {
            visibility = View.GONE
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.databaseEnabled = true
            // SSO chain crosses origins (Microsoft → Schulnetz). Without this,
            // 3rd-party cookies set inside redirects are dropped.
            CookieManager.getInstance().setAcceptCookie(true)
            CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
        }

        // ---- tab context shared across all tabs ----
        val tabCtx = TabContext(
            activity = this,
            prefs = prefs,
            scope = scope,
            sharedWebView = sharedWebView,
            getApiBase = { apiBaseInput.text.toString().trimEnd('/') },
            getSchulnetzBase = { schulnetzBaseInput.text.toString().trimEnd('/') },
        )

        // ---- build the four tab views ----
        val sections: List<Pair<String, TabSection>> = listOf(
            "Auth"         to AuthTab(),
            "Refresh"      to RefreshTab(),
            "Webscrape"    to WebscrapeTab(),
            "Mobile Proxy" to ProxyTab(),
        )
        val tabViews = sections.map { (_, section) -> section.build(tabCtx) }

        val tabLayout = TabLayout(this).apply {
            sections.forEach { (label, _) -> addTab(newTab().setText(label)) }
            tabMode = TabLayout.MODE_SCROLLABLE
        }

        val container = FrameLayout(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
        }
        tabViews.forEach { view ->
            container.addView(view, FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            ))
            view.visibility = View.GONE
        }
        tabViews.first().visibility = View.VISIBLE
        // The shared WebView lives inside the container as the top child so it
        // overlays the active tab fullscreen when an OAuth flow is in progress.
        container.addView(sharedWebView, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
        ))

        tabLayout.addOnTabSelectedListener(object : TabLayout.OnTabSelectedListener {
            override fun onTabSelected(tab: TabLayout.Tab) {
                tabViews.forEach { it.visibility = View.GONE }
                tabViews[tab.position].visibility = View.VISIBLE
                // Hide the WebView when switching tabs — only OAuth flows show it.
                sharedWebView.visibility = View.GONE
            }
            override fun onTabUnselected(tab: TabLayout.Tab) {}
            override fun onTabReselected(tab: TabLayout.Tab) {}
        })

        // ---- assemble ----
        listOf<View>(apiBaseInput, schulnetzBaseInput, clearBtn, tabLayout, container)
            .forEach { root.addView(it) }
        setContentView(root)

        clearBtn.setOnClickListener {
            prefs.edit().clear().apply()
            // Reseed the base URL fields so they don't go blank.
            persistBaseInputs()
        }

        // Persist base URLs on every text change so they survive process death.
        apiBaseInput.setOnFocusChangeListener { _, hasFocus -> if (!hasFocus) persistBaseInputs() }
        schulnetzBaseInput.setOnFocusChangeListener { _, hasFocus -> if (!hasFocus) persistBaseInputs() }
    }

    private fun persistBaseInputs() {
        prefs.edit()
            .putString("api_base", apiBaseInput.text.toString())
            .putString("schulnetz_base", schulnetzBaseInput.text.toString())
            .apply()
    }

    private fun field(label: String, initial: String): EditText = EditText(this).apply {
        hint = label
        setText(initial)
    }
}

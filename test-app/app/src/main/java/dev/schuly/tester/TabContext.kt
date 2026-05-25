package dev.schuly.tester

import android.content.Context
import android.content.SharedPreferences
import android.webkit.WebView
import kotlinx.coroutines.CoroutineScope

/** Shared state and dependencies passed to every tab section. */
data class TabContext(
    val activity: Context,
    val prefs: SharedPreferences,
    val scope: CoroutineScope,
    val sharedWebView: WebView,
    val getApiBase: () -> String,
    val getSchulnetzBase: () -> String,
)

interface TabSection {
    /** Build and return this tab's root view. Called once at startup. */
    fun build(ctx: TabContext): android.view.View
}

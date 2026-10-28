package dev.schuly.tester

import java.net.HttpURLConnection
import java.net.URL

/** Shared HTTP helpers used by every tab. Sync — caller is expected to wrap in IO dispatcher. */
object Net {
    fun httpGet(url: String, bearer: String? = null, headers: Map<String, String> = emptyMap()): Pair<Int, String> = request("GET", url, null, bearer, headers)

    fun httpPost(url: String, json: String, bearer: String? = null, headers: Map<String, String> = emptyMap()): Pair<Int, String> = request("POST", url, json, bearer, headers)

    private fun request(method: String, url: String, json: String?, bearer: String?, headers: Map<String, String>): Pair<Int, String> = runCatching {
        val con = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 15_000
            readTimeout = 120_000
            setRequestProperty("Accept", "application/json")
            if (json != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
            if (bearer != null) setRequestProperty("Authorization", "Bearer $bearer")
            headers.forEach { (k, v) -> setRequestProperty(k, v) }
        }
        try {
            if (json != null) con.outputStream.use { it.write(json.toByteArray()) }
            val status = con.responseCode
            val text = (if (status in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            status to text
        } finally { con.disconnect() }
    }.getOrElse { -1 to "Request failed: ${it.message}" }
}

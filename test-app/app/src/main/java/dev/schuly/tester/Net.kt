package dev.schuly.tester

import java.net.HttpURLConnection
import java.net.URL

/** Shared HTTP helpers used by every tab. Sync — caller is expected to wrap in IO dispatcher. */
object Net {
    fun httpGet(url: String, bearer: String? = null): Pair<Int, String> = runCatching {
        val con = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 15_000
            readTimeout = 60_000
            setRequestProperty("Accept", "application/json")
            if (bearer != null) setRequestProperty("Authorization", "Bearer $bearer")
        }
        try {
            val status = con.responseCode
            val text = (if (status in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            status to text
        } finally { con.disconnect() }
    }.getOrElse { -1 to "Request failed: ${it.message}" }

    fun httpPost(url: String, json: String, bearer: String? = null): Pair<Int, String> = runCatching {
        val con = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = 15_000
            readTimeout = 120_000
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
            if (bearer != null) setRequestProperty("Authorization", "Bearer $bearer")
        }
        try {
            con.outputStream.use { it.write(json.toByteArray()) }
            val status = con.responseCode
            val text = (if (status in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""
            status to text
        } finally { con.disconnect() }
    }.getOrElse { -1 to "Request failed: ${it.message}" }
}

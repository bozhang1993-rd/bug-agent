package com.bugagent

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class LogService {
    private val baseUrl = "http://127.0.0.1:8765"
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    fun fetchRecentLogs(limit: Int = 100): List<LogEntry> {
        val url = "$baseUrl/logs?limit=$limit"
        
        val request = Request.Builder()
            .url(url)
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("获取日志失败: ${response.code}")
        }
        
        val body = response.body?.string() ?: return emptyList()
        val json = JSONObject(body)
        
        val logs = mutableListOf<LogEntry>()
        val data = json.optJSONArray("data") ?: return logs
        
        for (i in 0 until data.length()) {
            val item = data.getJSONObject(i)
            logs.add(LogEntry(
                logId = item.optString("log_id", ""),
                timestamp = item.optString("timestamp", ""),
                level = item.optString("level", "INFO"),
                message = item.optString("message", ""),
                trace = item.optString("trace", null)
            ))
        }
        
        return logs
    }
}

data class LogEntry(
    val logId: String,
    val timestamp: String,
    val level: String,
    val message: String,
    val trace: String?
)

data class AnalysisResult(
    val errorType: String,
    val errorMessage: String,
    val location: Location?,
    val rootCause: String,
    val fixSuggestion: String,
    val fixCode: String,
    val confidence: Double,
    val codeContext: String?
)

data class Location(
    val file: String,
    val line: Int
)

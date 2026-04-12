package com.bugagent

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AnalysisService {
    private val baseUrl = "http://127.0.0.1:8765"
    private val client = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    fun analyze(errorContent: String): AnalysisResult {
        val url = "$baseUrl/analyze"
        
        val requestBody = JSONObject().apply {
            put("error_content", errorContent)
            put("auto_fix", false)
        }.toString().toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("分析失败: ${response.code} - ${response.message}")
        }
        
        val body = response.body?.string() ?: throw Exception("分析返回为空")
        val json = JSONObject(body)
        
        val location = json.optJSONObject("location")?.let {
            Location(
                file = it.optString("file", ""),
                line = it.optInt("line", 0)
            )
        }
        
        return AnalysisResult(
            errorType = json.optString("error_type", "UNKNOWN"),
            errorMessage = json.optString("error_message", ""),
            location = location,
            rootCause = json.optString("root_cause", ""),
            fixSuggestion = json.optString("fix_suggestion", ""),
            fixCode = json.optString("fix_code", ""),
            confidence = json.optDouble("confidence", 0.0),
            codeContext = json.optString("code_context", null)
        )
    }

    fun applyFix(filePath: String, lineNumber: Int, fixCode: String): Boolean {
        val url = "$baseUrl/fix"
        
        val requestBody = JSONObject().apply {
            put("file_path", filePath)
            put("line_number", lineNumber)
            put("fix_code", fixCode)
        }.toString().toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            return false
        }
        
        val body = response.body?.string() ?: return false
        val json = JSONObject(body)
        
        return json.optBoolean("success", false)
    }
}

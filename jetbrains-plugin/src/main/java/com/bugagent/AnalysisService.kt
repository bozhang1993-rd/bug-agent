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

    // ============ 异常分析 ============

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
        
        return executeRequest(request)
    }

    fun analyzeEnhanced(filePath: String, lineNumber: Int, errorType: String?, errorMessage: String?): EnhancedAnalysisResult {
        val url = "$baseUrl/analyze/enhanced"
        
        val requestBody = JSONObject().apply {
            put("file_path", filePath)
            put("line_number", lineNumber)
            put("error_type", errorType ?: "")
            put("error_message", errorMessage ?: "")
        }.toString().toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("增强分析失败: ${response.code}")
        }
        
        val body = response.body?.string() ?: throw Exception("返回为空")
        val json = JSONObject(body)
        
        val location = json.optJSONObject("location")
        val methodInfo = json.optJSONObject("method_info")
        val callChain = json.optJSONObject("call_chain")
        
        return EnhancedAnalysisResult(
            errorType = json.optString("error_type", "UNKNOWN"),
            errorMessage = json.optString("error_message", ""),
            location = location?.let {
                Location(it.optString("file", ""), it.optInt("line", 0))
            },
            methodInfo = methodInfo?.let { parseMethodInfo(it) },
            callChain = callChain?.let { parseCallChain(it) },
            fullMethod = json.optString("full_method", ""),
            errorCategory = json.optJSONObject("error_category")?.toMap(),
            rootCause = json.optString("root_cause", ""),
            fixSuggestion = json.optString("fix_suggestion", ""),
            fixCode = json.optString("fix_code", ""),
            confidence = json.optDouble("confidence", 0.0)
        )
    }

    private fun parseMethodInfo(json: JSONObject): MethodInfo {
        return MethodInfo(
            name = json.optString("name", ""),
            className = json.optString("class", ""),
            modifier = json.optString("modifier", ""),
            params = json.optString("params", ""),
            start = json.optInt("start", 0),
            end = json.optInt("end", 0)
        )
    }

    private fun parseCallChain(json: JSONObject): CallChain {
        val calls = mutableListOf<MethodCall>()
        val calledBy = mutableListOf<MethodCall>()
        
        json.optJSONArray("calls")?.let { arr ->
            for (i in 0 until arr.length()) {
                val item = arr.getJSONObject(i)
                calls.add(MethodCall(
                    obj = item.optString("object", ""),
                    method = item.optString("method", ""),
                    line = item.optInt("line", 0)
                ))
            }
        }
        
        json.optJSONArray("called_by")?.let { arr ->
            for (i in 0 until arr.length()) {
                val item = arr.getJSONObject(i)
                calledBy.add(MethodCall(
                    obj = item.optString("class", ""),
                    method = item.optString("method", ""),
                    line = item.optInt("line", 0)
                ))
            }
        }
        
        return CallChain(calls, calledBy)
    }

    // ============ 交互式分析 ============

    fun startInteractive(): InteractiveStartResult {
        val url = "$baseUrl/analyze/interactive/start"
        
        val request = Request.Builder()
            .url(url)
            .post("".toRequestBody("application/json".toMediaType()))
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("开始交互式分析失败: ${response.code}")
        }
        
        val json = JSONObject(response.body?.string())
        
        return InteractiveStartResult(
            sessionId = json.optString("session_id", ""),
            status = json.optString("status", ""),
            question = json.optJSONObject("question")?.let { q ->
                InteractiveQuestion(q.optString("key", ""), q.optString("question", ""))
            },
            progress = json.optString("progress", "")
        )
    }

    fun answerInteractive(sessionId: String, answer: String): InteractiveAnswerResult {
        val url = "$baseUrl/analyze/interactive/answer?session_id=$sessionId&answer=$answer"
        
        val request = Request.Builder()
            .url(url)
            .post("".toRequestBody("application/json".toMediaType()))
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("回答问题失败: ${response.code}")
        }
        
        val json = JSONObject(response.body?.string())
        
        return InteractiveAnswerResult(
            sessionId = json.optString("session_id", ""),
            status = json.optString("status", ""),
            question = json.optJSONObject("question")?.let { q ->
                InteractiveQuestion(q.optString("key", ""), q.optString("question", ""))
            },
            progress = json.optString("progress", ""),
            result = if (json.has("result")) json.optJSONObject("result")?.toMap() else null
        )
    }

    fun getInteractiveStatus(sessionId: String): InteractiveStatusResult {
        val url = "$baseUrl/analyze/interactive/status/$sessionId"
        
        val request = Request.Builder()
            .url(url)
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("获取状态失败: ${response.code}")
        }
        
        val json = JSONObject(response.body?.string())
        
        return InteractiveStatusResult(
            sessionId = json.optString("session_id", ""),
            status = json.optString("status", ""),
            progress = json.optString("progress", ""),
            result = if (json.has("result")) json.optJSONObject("result")?.toMap() else null
        )
    }

    // ============ 业务分析 ============

    fun analyzeWorkflow(workflow: String, code: String): WorkflowResult {
        val url = "$baseUrl/analyze/workflow"
        
        val requestBody = JSONObject().apply {
            put("workflow_description", workflow)
            put("code", code)
            put("language", "java")
        }.toString().toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        return executeWorkflowRequest(request)
    }

    fun compareWorkflow(expected: String, actualCode: String): WorkflowResult {
        val url = "$baseUrl/analyze/workflow/compare"
        
        val requestBody = JSONObject().apply {
            put("expected_workflow", expected)
            put("actual_code", actualCode)
            put("language", "java")
        }.toString().toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        return executeWorkflowRequest(request)
    }

    private fun executeWorkflowRequest(request: Request): WorkflowResult {
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("业务分析失败: ${response.code}")
        }
        
        val json = JSONObject(response.body?.string())
        
        return WorkflowResult(
            analysis = json.optString("符合性分析", ""),
            issues = json.optString("问题点", ""),
            fixSuggestion = json.optString("修复建议", ""),
            fixCode = json.optString("修正代码", "")
        )
    }

    // ============ 文档检索 ============

    fun searchDocs(keyword: String): List<DocSearchResult> {
        val url = "$baseUrl/docs/search?keyword=$keyword"
        
        val request = Request.Builder()
            .url(url)
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("搜索文档失败: ${response.code}")
        }
        
        val json = JSONObject(response.body?.string())
        val results = mutableListOf<DocSearchResult>()
        
        json.optJSONArray("results")?.let { arr ->
            for (i in 0 until arr.length()) {
                val item = arr.getJSONObject(i)
                val matches = mutableListOf<String>()
                item.optJSONArray("matches")?.let { mArr ->
                    for (j in 0 until mArr.length()) {
                        matches.add(mArr.getString(j))
                    }
                }
                results.add(DocSearchResult(
                    file = item.optString("file", ""),
                    title = item.optString("title", ""),
                    matches = matches,
                    docType = item.optString("doc_type", "")
                ))
            }
        }
        
        return results
    }

    fun searchRules(keyword: String): List<RuleSearchResult> {
        val url = "$baseUrl/rules/search?keyword=$keyword"
        
        val request = Request.Builder()
            .url(url)
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("搜索规则失败: ${response.code}")
        }
        
        val json = JSONObject(response.body?.string())
        val rules = mutableListOf<RuleSearchResult>()
        
        json.optJSONArray("rules")?.let { arr ->
            for (i in 0 until arr.length()) {
                val item = arr.getJSONObject(i)
                rules.add(RuleSearchResult(
                    rule = item.optString("rule", ""),
                    source = item.optString("source", "")
                ))
            }
        }
        
        return rules
    }

    // ============ 修复 ============

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
        
        val json = JSONObject(response.body?.string())
        return json.optBoolean("success", false)
    }

    // ============ 辅助方法 ============

    private fun executeRequest(request: Request): AnalysisResult {
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("分析失败: ${response.code}")
        }
        
        val body = response.body?.string() ?: throw Exception("分析返回为空")
        val json = JSONObject(body)
        
        val location = json.optJSONObject("location")?.let {
            Location(
                file = it.optString("file", ""),
                line = it.optInt("line", 0)
            )
        }
        
        val errorCategory = json.optJSONObject("error_category")?.toMap()
        
        return AnalysisResult(
            errorType = json.optString("error_type", "UNKNOWN"),
            errorMessage = json.optString("error_message", ""),
            location = location,
            errorCategory = errorCategory,
            rootCause = json.optString("root_cause", ""),
            fixSuggestion = json.optString("fix_suggestion", ""),
            fixCode = json.optString("fix_code", ""),
            confidence = json.optDouble("confidence", 0.0),
            codeContext = json.optString("code_context", null)
        )
    }

    private fun JSONObject.toMap(): Map<String, Any?> {
        val map = mutableMapOf<String, Any?>()
        keys().forEach { key ->
            map[key] = get(key)
        }
        return map
    }
}

// ============ 数据类 ============

data class Location(val file: String, val line: Int)

data class AnalysisResult(
    val errorType: String,
    val errorMessage: String,
    val location: Location?,
    val errorCategory: Map<String, Any>?,
    val rootCause: String,
    val fixSuggestion: String,
    val fixCode: String,
    val confidence: Double,
    val codeContext: String?
)

data class EnhancedAnalysisResult(
    val errorType: String,
    val errorMessage: String,
    val location: Location?,
    val methodInfo: MethodInfo?,
    val callChain: CallChain?,
    val fullMethod: String,
    val errorCategory: Map<String, Any>?,
    val rootCause: String,
    val fixSuggestion: String,
    val fixCode: String,
    val confidence: Double
)

data class MethodInfo(
    val name: String,
    val className: String,
    val modifier: String,
    val params: String,
    val start: Int,
    val end: Int
)

data class CallChain(val calls: List<MethodCall>, val calledBy: List<MethodCall>)

data class MethodCall(val obj: String, val method: String, val line: Int)

data class InteractiveStartResult(
    val sessionId: String,
    val status: String,
    val question: InteractiveQuestion?,
    val progress: String
)

data class InteractiveQuestion(val key: String, val question: String)

data class InteractiveAnswerResult(
    val sessionId: String,
    val status: String,
    val question: InteractiveQuestion?,
    val progress: String,
    val result: Map<String, Any?>?
)

data class InteractiveStatusResult(
    val sessionId: String,
    val status: String,
    val progress: String,
    val result: Map<String, Any?>?
)

data class WorkflowResult(
    val analysis: String,
    val issues: String,
    val fixSuggestion: String,
    val fixCode: String
)

data class DocSearchResult(
    val file: String,
    val title: String,
    val matches: List<String>,
    val docType: String
)

data class RuleSearchResult(
    val rule: String,
    val source: String
)
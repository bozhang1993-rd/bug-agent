package com.bugagent

import com.intellij.openapi.project.Project
import com.intellij.ui.components.JBTextArea
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.components.JBTabbedPane
import java.awt.*
import javax.swing.*

class ToolWindowForm(private val project: Project) {
    private val logService = LogService()
    private val analysisService = AnalysisService()
    
    // Tab 1: 异常分析
    private val errorInputArea = JBTextArea(8, 50).apply {
        lineWrap = true
        wrapStyleWord = true
        font = Font("Monospaced", Font.PLAIN, 12)
    }
    
    // Tab 2: 交互式分析
    private val interactiveArea = JBTextArea(6, 50).apply {
        lineWrap = true
        wrapStyleWord = true
        font = Font("Monospaced", Font.PLAIN, 12)
    }
    
    // Tab 3: 业务分析
    private val workflowInputArea = JBTextArea(4, 50).apply {
        lineWrap = true
        wrapStyleWord = true
        font = Font("Monospaced", Font.PLAIN, 12)
    }
    
    private val resultArea = JBTextArea(20, 50).apply {
        isEditable = false
        lineWrap = true
        wrapStyleWord = true
        font = Font("Monospaced", Font.PLAIN, 12)
        background = Color(245, 245, 245)
    }
    
    private val statusLabel = JLabel("就绪")
    
    // Tab 1 按钮
    private val analyzeButton = JButton("分析错误")
    private val analyzeEnhancedButton = JButton("增强分析")
    private val fetchLogsButton = JButton("获取日志")
    private val fixButton = JButton("应用修复")
    
    // Tab 2 按钮
    private val startInteractiveButton = JButton("开始交互式分析")
    private val answerButton = JButton("回答问题")
    private val nextQuestionButton = JButton("下一问题")
    
    // Tab 3 按钮
    private val analyzeWorkflowButton = JButton("分析业务流程")
    private val searchDocsButton = JButton("搜索文档")
    private val searchRulesButton = JButton("搜索规则")
    
    private var currentAnalysisResult: AnalysisResult? = null
    private var currentInteractiveSession: String? = null
    
    fun getContent(): JComponent {
        val tabbedPane = JBTabbedPane()
        
        // Tab 1: 异常分析
        val tab1 = createExceptionTab()
        tabbedPane.addTab("异常分析", tab1)
        
        // Tab 2: 交互式分析
        val tab2 = createInteractiveTab()
        tabbedPane.addTab("交互式分析", tab2)
        
        // Tab 3: 业务分析
        val tab3 = createBusinessTab()
        tabbedPane.addTab("业务分析", tab3)
        
        return tabbedPane
    }
    
    private fun createExceptionTab(): JComponent {
        val panel = JPanel(BorderLayout(10, 10))
        
        val inputPanel = JPanel(BorderLayout())
        inputPanel.add(JLabel("错误信息 (StackTrace):"), BorderLayout.NORTH)
        inputPanel.add(JBScrollPane(errorInputArea), BorderLayout.CENTER)
        
        val buttonPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 5))
        buttonPanel.add(analyzeButton)
        buttonPanel.add(analyzeEnhancedButton)
        buttonPanel.add(fetchLogsButton)
        buttonPanel.add(fixButton)
        
        val centerPanel = JPanel(BorderLayout(5, 5))
        centerPanel.add(inputPanel, BorderLayout.NORTH)
        centerPanel.add(buttonPanel, BorderLayout.CENTER)
        
        val resultPanel = JPanel(BorderLayout())
        resultPanel.add(JLabel("分析结果:"), BorderLayout.NORTH)
        resultPanel.add(JBScrollPane(resultArea), BorderLayout.CENTER)
        
        val bottomPanel = JPanel(BorderLayout())
        bottomPanel.add(statusLabel, BorderLayout.WEST)
        
        panel.add(centerPanel, BorderLayout.NORTH)
        panel.add(resultPanel, BorderLayout.CENTER)
        panel.add(bottomPanel, BorderLayout.SOUTH)
        
        analyzeButton.addActionListener { analyzeError() }
        analyzeEnhancedButton.addActionListener { analyzeEnhancedError() }
        fetchLogsButton.addActionListener { fetchLogs() }
        fixButton.addActionListener { applyFix() }
        
        return panel
    }
    
    private fun createInteractiveTab(): JComponent {
        val panel = JPanel(BorderLayout(10, 10))
        
        val inputPanel = JPanel(BorderLayout())
        inputPanel.add(JLabel("交互式问答:"), BorderLayout.NORTH)
        inputPanel.add(JBScrollPane(interactiveArea), BorderLayout.CENTER)
        
        val buttonPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 5))
        buttonPanel.add(startInteractiveButton)
        buttonPanel.add(answerButton)
        
        val centerPanel = JPanel(BorderLayout(5, 5))
        centerPanel.add(inputPanel, BorderLayout.NORTH)
        centerPanel.add(buttonPanel, BorderLayout.CENTER)
        
        val resultPanel = JPanel(BorderLayout())
        resultPanel.add(JLabel("分析结果:"), BorderLayout.NORTH)
        resultPanel.add(JBScrollPane(resultArea), BorderLayout.CENTER)
        
        val bottomPanel = JPanel(BorderLayout())
        bottomPanel.add(statusLabel, BorderLayout.WEST)
        
        panel.add(centerPanel, BorderLayout.NORTH)
        panel.add(resultPanel, BorderLayout.CENTER)
        panel.add(bottomPanel, BorderLayout.SOUTH)
        
        startInteractiveButton.addActionListener { startInteractive() }
        answerButton.addActionListener { answerInteractive() }
        
        return panel
    }
    
    private fun createBusinessTab(): JComponent {
        val panel = JPanel(BorderLayout(10, 10))
        
        val inputPanel = JPanel(BorderLayout())
        inputPanel.add(JLabel("业务流程描述:"), BorderLayout.NORTH)
        inputPanel.add(JBScrollPane(workflowInputArea), BorderLayout.CENTER)
        
        val buttonPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 5))
        buttonPanel.add(analyzeWorkflowButton)
        buttonPanel.add(searchDocsButton)
        buttonPanel.add(searchRulesButton)
        
        val centerPanel = JPanel(BorderLayout(5, 5))
        centerPanel.add(inputPanel, BorderLayout.NORTH)
        centerPanel.add(buttonPanel, BorderLayout.CENTER)
        
        val resultPanel = JPanel(BorderLayout())
        resultPanel.add(JLabel("分析结果:"), BorderLayout.NORTH)
        resultPanel.add(JBScrollPane(resultArea), BorderLayout.CENTER)
        
        val bottomPanel = JPanel(BorderLayout())
        bottomPanel.add(statusLabel, BorderLayout.WEST)
        
        panel.add(centerPanel, BorderLayout.NORTH)
        panel.add(resultPanel, BorderLayout.CENTER)
        panel.add(bottomPanel, BorderLayout.SOUTH)
        
        analyzeWorkflowButton.addActionListener { analyzeWorkflow() }
        searchDocsButton.addActionListener { searchDocs() }
        searchRulesButton.addActionListener { searchRules() }
        
        return panel
    }
    
    // ============ Tab 1: 异常分析功能 ============
    
    private fun analyzeError() {
        val errorContent = errorInputArea.text.trim()
        if (errorContent.isEmpty()) {
            updateStatus("请输入错误信息")
            return
        }
        
        updateStatus("分析中...")
        
        try {
            val result = analysisService.analyze(errorContent)
            currentAnalysisResult = result
            
            val output = buildString {
                appendLine("=== 错误类型 ===")
                appendLine(result.errorType)
                appendLine()
                appendLine("=== 错误分类 ===")
                result.errorCategory?.let { cat ->
                    appendLine("分类: ${cat["category"] ?: "未知"}")
                    appendLine("可能原因: ${cat["likely_cause"] ?: ""}")
                    appendLine()
                }
                appendLine("=== 错误消息 ===")
                appendLine(result.errorMessage)
                appendLine()
                result.location?.let {
                    appendLine("=== 错误位置 ===")
                    appendLine("文件: ${it.file}")
                    appendLine("行号: ${it.line}")
                    appendLine()
                }
                appendLine("=== 根因分析 ===")
                appendLine(result.rootCause)
                appendLine()
                appendLine("=== 修复建议 ===")
                appendLine(result.fixSuggestion)
                appendLine()
                if (result.fixCode.isNotEmpty()) {
                    appendLine("=== 修复代码 ===")
                    appendLine(result.fixCode)
                    appendLine()
                }
                appendLine("置信度: ${result.confidence}")
            }
            
            resultArea.text = output
            updateStatus("分析完成")
        } catch (e: Exception) {
            updateStatus("分析失败: ${e.message}")
            resultArea.text = "错误: ${e.message}"
        }
    }
    
    private fun analyzeEnhancedError() {
        val errorContent = errorInputArea.text.trim()
        if (errorContent.isEmpty()) {
            updateStatus("请输入包含文件路径和行号的错误信息")
            return
        }
        
        updateStatus("增强分析中...")
        
        // TODO: 需要用户输入文件路径和行号，这里暂时用简单方式
        updateStatus("增强分析需要指定文件路径和行号")
    }
    
    private fun fetchLogs() {
        updateStatus("获取日志...")
        
        try {
            val logs = logService.fetchRecentLogs()
            
            val output = buildString {
                appendLine("=== 最近日志 ===")
                logs.forEachIndexed { index, log ->
                    appendLine("${index + 1}. [${log.level}] ${log.message}")
                    log.trace?.let {
                        appendLine("   堆栈: ${it.take(200)}...")
                    }
                    appendLine()
                }
            }
            
            resultArea.text = output
            updateStatus("获取完成，共 ${logs.size} 条")
        } catch (e: Exception) {
            updateStatus("获取日志失败: ${e.message}")
        }
    }
    
    private fun applyFix() {
        val result = currentAnalysisResult ?: run {
            updateStatus("没有可应用的修复")
            return
        }
        
        if (result.location == null || result.fixCode.isEmpty()) {
            updateStatus("没有可应用的修复")
            return
        }
        
        try {
            val success = analysisService.applyFix(
                result.location.file,
                result.location.line,
                result.fixCode
            )
            
            updateStatus(if (success) "修复已应用" else "修复应用失败")
        } catch (e: Exception) {
            updateStatus("修复应用失败: ${e.message}")
        }
    }
    
    // ============ Tab 2: 交互式分析功能 ============
    
    private fun startInteractive() {
        updateStatus("开始交互式分析...")
        
        try {
            val result = analysisService.startInteractive()
            currentInteractiveSession = result.sessionId
            
            val output = buildString {
                appendLine("=== 交互式分析已开始 ===")
                appendLine("会话ID: ${result.sessionId}")
                appendLine("进度: ${result.progress}")
                appendLine()
                result.question?.let {
                    appendLine("=== 问题 ===")
                    appendLine(it.question)
                }
            }
            
            resultArea.text = output
            updateStatus("请回答问题")
        } catch (e: Exception) {
            updateStatus("启动失败: ${e.message}")
        }
    }
    
    private fun answerInteractive() {
        val sessionId = currentInteractiveSession
        if (sessionId == null) {
            updateStatus("请先开始交互式分析")
            return
        }
        
        val answer = interactiveArea.text.trim()
        if (answer.isEmpty()) {
            updateStatus("请输入回答")
            return
        }
        
        updateStatus("提交回答中...")
        
        try {
            val result = analysisService.answerInteractive(sessionId, answer)
            
            val output = buildString {
                appendLine("=== 回答已提交 ===")
                appendLine("进度: ${result.progress}")
                appendLine("状态: ${result.status}")
                appendLine()
                
                result.result?.let { res ->
                    appendLine("=== 分析结果 ===")
                    res["root_cause"]?.let { appendLine("根因: $it") }
                    res["fix_suggestion"]?.let { appendLine("建议: $it") }
                    res["fix_code"]?.let { appendLine("代码: $it") }
                } ?: run {
                    result.question?.let {
                        appendLine("=== 下一问题 ===")
                        appendLine(it.question)
                    }
                }
            }
            
            resultArea.text = output
            updateStatus(if (result.status == "completed") "分析完成" else "继续回答")
        } catch (e: Exception) {
            updateStatus("回答失败: ${e.message}")
        }
    }
    
    // ============ Tab 3: 业务分析功能 ============
    
    private fun analyzeWorkflow() {
        val workflow = workflowInputArea.text.trim()
        if (workflow.isEmpty()) {
            updateStatus("请输入业务流程描述")
            return
        }
        
        updateStatus("分析业务流程...")
        
        try {
            val result = analysisService.analyzeWorkflow(workflow, "")
            
            val output = buildString {
                appendLine("=== 业务流程分析 ===")
                appendLine()
                appendLine("=== 符合性分析 ===")
                appendLine(result.analysis)
                appendLine()
                if (result.issues.isNotEmpty()) {
                    appendLine("=== 问题点 ===")
                    appendLine(result.issues)
                    appendLine()
                }
                if (result.fixSuggestion.isNotEmpty()) {
                    appendLine("=== 修复建议 ===")
                    appendLine(result.fixSuggestion)
                    appendLine()
                }
                if (result.fixCode.isNotEmpty()) {
                    appendLine("=== 修正代码 ===")
                    appendLine(result.fixCode)
                }
            }
            
            resultArea.text = output
            updateStatus("分析完成")
        } catch (e: Exception) {
            updateStatus("分析失败: ${e.message}")
        }
    }
    
    private fun searchDocs() {
        val keyword = workflowInputArea.text.trim()
        if (keyword.isEmpty()) {
            updateStatus("请输入搜索关键词")
            return
        }
        
        updateStatus("搜索文档...")
        
        try {
            val results = analysisService.searchDocs(keyword)
            
            val output = buildString {
                appendLine("=== 搜索结果 ===")
                appendLine()
                results.forEachIndexed { index, doc ->
                    appendLine("${index + 1}. ${doc.title}")
                    appendLine("   文件: ${doc.file}")
                    appendLine("   类型: ${doc.docType}")
                    if (doc.matches.isNotEmpty()) {
                        appendLine("   匹配内容:")
                        doc.matches.take(2).forEach { match ->
                            appendLine("     - ${match.take(100)}")
                        }
                    }
                    appendLine()
                }
            }
            
            resultArea.text = output
            updateStatus("找到 ${results.size} 个结果")
        } catch (e: Exception) {
            updateStatus("搜索失败: ${e.message}")
        }
    }
    
    private fun searchRules() {
        val keyword = workflowInputArea.text.trim()
        if (keyword.isEmpty()) {
            updateStatus("请输入搜索关键词")
            return
        }
        
        updateStatus("搜索业务规则...")
        
        try {
            val results = analysisService.searchRules(keyword)
            
            val output = buildString {
                appendLine("=== 业务规则搜索结果 ===")
                appendLine()
                results.forEachIndexed { index, rule ->
                    appendLine("${index + 1}. ${rule.rule}")
                    appendLine("   来源: ${rule.source}")
                    appendLine()
                }
            }
            
            resultArea.text = output
            updateStatus("找到 ${results.size} 条规则")
        } catch (e: Exception) {
            updateStatus("搜索失败: ${e.message}")
        }
    }
    
    private fun updateStatus(message: String) {
        statusLabel.text = message
    }
}
package com.bugagent

import com.intellij.openapi.project.Project
import com.intellij.ui.components.JBTextArea
import com.intellij.ui.components.JBScrollPane
import java.awt.*
import javax.swing.*

class ToolWindowForm(private val project: Project) {
    private val logService = LogService()
    private val analysisService = AnalysisService()
    
    private val errorInputArea = JBTextArea(8, 50).apply {
        lineWrap = true
        wrapStyleWord = true
        font = Font("Monospaced", Font.PLAIN, 12)
    }
    
    private val resultArea = JBTextArea(15, 50).apply {
        isEditable = false
        lineWrap = true
        wrapStyleWord = true
        font = Font("Monospaced", Font.PLAIN, 12)
        background = Color(245, 245, 245)
    }
    
    private val statusLabel = JLabel("就绪")
    private val analyzeButton = JButton("分析错误")
    private val fixButton = JButton("应用修复")
    private val fetchLogsButton = JButton("获取日志")
    
    private var currentAnalysisResult: AnalysisResult? = null
    
    fun getContent(): JComponent {
        val panel = JPanel(BorderLayout(10, 10))
        panel.border = BorderFactory.createEmptyBorder(10, 10, 10, 10)
        
        val topPanel = JPanel(BorderLayout())
        topPanel.add(JLabel("错误信息 (StackTrace):"), BorderLayout.NORTH)
        
        val errorScroll = JBScrollPane(errorInputArea)
        errorScroll.preferredSize = Dimension(0, 150)
        
        val buttonPanel = JPanel(FlowLayout(FlowLayout.LEFT, 5, 5))
        buttonPanel.add(analyzeButton)
        buttonPanel.add(fetchLogsButton)
        buttonPanel.add(fixButton)
        
        val centerPanel = JPanel(BorderLayout(5, 5))
        centerPanel.add(errorScroll, BorderLayout.NORTH)
        centerPanel.add(buttonPanel, BorderLayout.CENTER)
        
        val resultPanel = JPanel(BorderLayout())
        resultPanel.add(JLabel("分析结果:"), BorderLayout.NORTH)
        
        val resultScroll = JBScrollPane(resultArea)
        
        val bottomPanel = JPanel(BorderLayout())
        bottomPanel.add(statusLabel, BorderLayout.WEST)
        
        val mainPanel = JPanel(BorderLayout(10, 10))
        mainPanel.add(centerPanel, BorderLayout.NORTH)
        mainPanel.add(resultScroll, BorderLayout.CENTER)
        mainPanel.add(bottomPanel, BorderLayout.SOUTH)
        
        mainPanel.addComponentListener(object : java.awt.event.ComponentAdapter() {
            override fun componentResized(e: java.awt.event.ComponentEvent?) {
                val d = mainPanel.size
                errorScroll.minimumSize = Dimension(d.width, 100)
                resultScroll.minimumSize = Dimension(d.width, 200)
            }
        })
        
        initListeners()
        
        return mainPanel
    }
    
    private fun initListeners() {
        analyzeButton.addActionListener { analyzeError() }
        fetchLogsButton.addActionListener { fetchLogs() }
        fixButton.addActionListener { applyFix() }
    }
    
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
    
    private fun updateStatus(message: String) {
        statusLabel.text = message
    }
}

package com.bugagent

import com.intellij.openapi.project.Project
import com.intellij.openapi.w.ToolWindow
import com.intellij.openapi.w.ToolWindowFactory
import com.intellij.ui.content.ContentFactory

class ToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val toolWindowForm = ToolWindowForm(project)
        val content = ContentFactory.getInstance().createContent(
            toolWindowForm.getContent(),
            "Bug Agent",
            false
        )
        toolWindow.contentManager.addContent(content)
    }
}

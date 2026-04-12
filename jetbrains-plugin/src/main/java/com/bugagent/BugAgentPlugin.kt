package com.bugagent

import com.intellij.openapi.components.ApplicationComponent
import com.intellij.openapi.diagnostic.Logger

class BugAgentPlugin : ApplicationComponent {
    private val logger = Logger.getInstance(BugAgentPlugin::class.java)

    override fun initComponent() {
        logger.info("Bug Agent 插件已启动")
    }

    override fun disposeComponent() {
        logger.info("Bug Agent 插件已卸载")
    }

    override fun getComponentName(): String = "BugAgentPlugin"
}

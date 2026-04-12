from typing import Dict, Any, List, Optional
import re
from .llm.client import LLMClient


class WorkflowAnalyzer:
    """业务流程分析器"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def analyze(
        self,
        workflow_description: str,
        code: str,
        language: str = "java"
    ) -> Dict[str, Any]:
        """分析业务流程是否符合预期"""
        
        prompt = self._build_analysis_prompt(workflow_description, code, language)
        
        messages = [
            {"role": "system", "content": "你是一个资深的业务分析师，擅长分析代码逻辑是否符合业务流程。请仔细对比业务流程描述和实际代码。"},
            {"role": "user", "content": prompt}
        ]
        
        result = self.llm_client.chat(messages)
        
        return self._parse_result(result)
    
    def compare(
        self,
        expected_workflow: str,
        actual_code: str,
        language: str = "java"
    ) -> Dict[str, Any]:
        """对比预期流程和实际代码"""
        
        prompt = self._build_comparison_prompt(expected_workflow, actual_code, language)
        
        messages = [
            {"role": "system", "content": "你是一个代码审查专家，擅长对比业务流程和代码实现，找出不一致的地方。"},
            {"role": "user", "content": prompt}
        ]
        
        result = self.llm_client.chat(messages)
        
        return self._parse_result(result)
    
    def _build_analysis_prompt(
        self,
        workflow_description: str,
        code: str,
        language: str
    ) -> str:
        return f"""## 业务流程描述

{workflow_description}

## 实际代码 ({language})

```
{code}
```

## 分析要求

请仔细分析上述代码是否符合业务流程描述：

### 1. 流程符合性
- 代码是否实现了业务流程描述中的功能
- 是否遗漏了某些步骤

### 2. 逻辑正确性
- 业务逻辑是否正确
- 计算逻辑是否正确

### 3. 边界处理
- 是否处理了边界情况
- 是否处理了异常情况

请按以下格式回复：

### 符合性分析
（代码是否符合业务流程）

### 问题点
（如果不符合，指出具体问题）

### 修复建议
（如何修复）

### 正确代码示例
（如需要，给出修正后的代码）

"""
    
    def _build_comparison_prompt(
        self,
        expected_workflow: str,
        actual_code: str,
        language: str
    ) -> str:
        return f"""## 预期业务流程

{expected_workflow}

## 实际代码 ({language})

```
{actual_code}
```

## 分析要求

请对比预期业务流程和实际代码，找出差异：

### 1. 流程差异
- 预期和实际的步骤差异

### 2. 逻辑差异
- 业务逻辑的差异

### 3. 计算差异
- 数值计算的差异（如有）

### 4. 具体问题
- 列出所有发现的问题

请按以下格式回复：

### 差异分析
（详细说明预期与实际的差异）

### 问题列表
（列出每个问题）

### 修复方案
（针对每个问题的修复建议）

### 修正代码
（修正后的代码）

"""
    
    def _parse_result(self, result: str) -> Dict[str, Any]:
        """解析分析结果"""
        analysis = {
            "符合性分析": "",
            "问题点": "",
            "修复建议": "",
            "修正代码": "",
            "问题列表": [],
            "差异分析": ""
        }
        
        lines = result.split("\n")
        current_section = None
        code_block = []
        in_code_block = False
        
        for line in lines:
            line_stripped = line.strip()
            
            if "符合性分析" in line_stripped or "差异分析" in line_stripped:
                current_section = "分析"
                continue
            elif "问题点" in line_stripped or "问题列表" in line_stripped:
                current_section = "问题"
                continue
            elif "修复建议" in line_stripped or "修复方案" in line_stripped:
                current_section = "修复"
                continue
            elif "正确代码" in line_stripped or "修正代码" in line_stripped:
                current_section = "代码"
                in_code_block = True
                continue
            
            if in_code_block:
                if line_stripped.startswith("```"):
                    in_code_block = False
                    continue
                if line_stripped:
                    code_block.append(line_stripped)
            elif current_section and line_stripped:
                if current_section == "分析":
                    analysis["符合性分析"] += line_stripped + "\n"
                elif current_section == "问题":
                    analysis["问题点"] += line_stripped + "\n"
                elif current_section == "修复":
                    analysis["修复建议"] += line_stripped + "\n"
        
        if code_block:
            analysis["修正代码"] = "\n".join(code_block)
        
        analysis["符合性分析"] = analysis["符合性分析"].strip()
        analysis["问题点"] = analysis["问题点"].strip()
        analysis["修复建议"] = analysis["修复建议"].strip()
        
        return analysis


class BusinessRuleExtractor:
    """业务规则提取器"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def extract_rules(self, document_content: str) -> List[str]:
        """从文档中提取业务规则"""
        
        prompt = f"""请从以下需求文档中提取出所有业务规则，每条规则用一句话描述：

{document_content[:5000]}

## 输出格式

请按以下格式输出：

1. [规则1描述]
2. [规则2描述]
3. [规则3描述]
...

"""
        
        messages = [
            {"role": "system", "content": "你是一个业务分析师，擅长提取和整理业务规则。"},
            {"role": "user", "content": prompt}
        ]
        
        result = self.llm_client.chat(messages)
        
        rules = []
        for line in result.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                rule = re.sub(r"^[\d\.\-\s]+", "", line).strip()
                if rule:
                    rules.append(rule)
        
        return rules
    
    def match_rule(self, code: str, rules: List[str]) -> Dict[str, Any]:
        """检查代码是否符合规则"""
        
        prompt = f"""请检查以下代码是否符合给定的业务规则：

## 代码

```
{code[:3000]}
```

## 业务规则

{chr(10).join([f"{i+1}. {rule}" for i, rule in enumerate(rules)])}

## 检查要求

请逐条检查代码是否符合每个规则，并给出结论。

请按以下格式回复：

### 检查结果

规则1：符合/不符合 - 原因
规则2：符合/不符合 - 原因
...

### 总结

（总体评估）

"""
        
        messages = [
            {"role": "system", "content": "你是一个代码审查专家，擅长检查代码是否符合业务规则。"},
            {"role": "user", "content": prompt}
        ]
        
        result = self.llm_client.chat(messages)
        
        return {
            "code": code[:500],
            "rules": rules,
            "check_result": result
        }

from typing import Dict, Any


def build_analysis_prompt(error_info: Dict[str, Any], code_context: str, error_type: str) -> str:
    exception_type = error_info.get("exception_type", "Unknown")
    exception_message = error_info.get("exception_message", "")
    first_frame = error_info.get("first_frame", "")
    
    prompt = f"""## 错误信息

**异常类型**: {exception_type}
**异常消息**: {exception_message}
**错误位置**: {first_frame}
**错误分类**: {error_type}

## 代码上下文

```
{code_context}
```

## 分析要求

请分析以上错误信息，结合代码上下文，找出问题的根本原因，并给出修复建议。

请按以下格式回复：

### 根因分析
（简要说明问题的根本原因）

### 修复建议
（具体的修复步骤和建议）

### 修复代码
（如果可以，给出修复后的代码片段）

"""
    return prompt


def build_fix_prompt(error_info: Dict[str, Any], code_context: str, fix_suggestion: str) -> str:
    exception_type = error_info.get("exception_type", "Unknown")
    first_frame = error_info.get("first_frame", "")
    
    prompt = f"""## 错误信息

**异常类型**: {exception_type}
**错误位置**: {first_frame}

## 当前代码

```
{code_context}
```

## 修复建议

{fix_suggestion}

请直接生成修复后的代码，不需要其他说明。

"""
    return prompt


def build_context_prompt(class_name: str, method_name: str, related_code: str) -> str:
    prompt = f"""## 相关代码

请分析以下代码，了解其业务逻辑：

```
{related_code}
```

这是 {class_name}.{method_name} 方法的相关代码，请结合这个上下文来分析错误。

"""
    return prompt

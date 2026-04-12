from typing import Dict, Any, List


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

请作为资深Java开发工程师，详细分析以上错误：

### 1. 根因分析
- 分析错误的直接原因
- 分析代码逻辑问题
- 分析可能的边界条件

### 2. 调用链分析
- 分析方法调用关系
- 分析变量来源

### 3. 修复方案
- 提供具体的修复步骤
- 如果可以，给出修复后的代码

### 4. 防御性建议
- 如何避免类似问题
- 需要增加哪些空值校验、边界检查

请按以下格式回复：

### 根因分析
（详细说明）

### 修复建议
（具体步骤）

### 修复代码
```
// 修复后的代码
```

### 防御建议
（如何预防）

"""
    return prompt


def build_enhanced_analysis_prompt(
    error_info: Dict[str, Any], 
    error_category: Dict[str, Any],
    method_info: Dict[str, Any],
    full_method: str,
    call_chain: Dict[str, Any],
    related_classes: list,
    error_type: str
) -> str:
    exception_type = error_info.get("exception_type", "Unknown")
    exception_message = error_info.get("exception_message", "")
    first_frame = error_info.get("first_frame", "")
    
    category = error_category.get("category", "UNKNOWN")
    sub_category = error_category.get("sub_category", "")
    likely_cause = error_category.get("likely_cause", "")
    analysis_focus = error_category.get("analysis_focus", [])
    
    method_name = method_info.get("name", "Unknown") if method_info else "Unknown"
    method_class = method_info.get("class", "Unknown") if method_info else "Unknown"
    method_modifier = method_info.get("modifier", "") if method_info else ""
    method_params = method_info.get("params", "") if method_info else ""
    
    calls = call_chain.get("calls", []) if call_chain else []
    called_by = call_chain.get("called_by", []) if call_chain else []
    
    prompt = f"""## 错误信息

- **异常类型**: {exception_type}
- **异常消息**: {exception_message}
- **错误位置**: {first_frame}
- **错误分类**: {error_type}

## 错误分类

- **问题类别**: {category}
- **子类别**: {sub_category}
- **可能原因**: {likely_cause}
- **分析重点**: {', '.join(analysis_focus)}

## 错误方法信息

- **方法名**: {method_name}
- **所属类**: {method_class}
- **访问修饰符**: {method_modifier}
- **参数**: {method_params}

## 完整方法代码

```
{full_method}
```

## 方法调用链

### 该方法调用的其他方法:
{calls[:10] if calls else "无"}

### 调用该方法的其他方法:
{called_by[:10] if called_by else "无"}

## 相关类 (通过 Import):
{related_classes[:5] if related_classes else "无"}

## 分析要求

请作为资深Java开发工程师，根据错误分类进行针对性分析：

### 1. 问题定位
- 根据分类 "{category}" 进行分析
- 重点关注: {', '.join(analysis_focus)}

### 2. 可能原因分析
- 如果是代码缺陷: 检查变量来源、添加空值校验
- 如果是上游问题: 检查调用方传参、检查上游数据
- 如果是数据库问题: 检查SQL、查看查询结果
- 如果是下游问题: 检查下游返回、处理异常情况

### 3. 修复方案
- 提供精确的修复位置和代码
- 考虑修复对调用链的影响

### 4. 最佳实践建议
- 如何写出更健壮的代码
- 需要添加哪些防御性检查

请按以下格式回复：

### 问题分析
（根据错误分类进行分析）

### 根因分析
（详细分析代码逻辑，找出真正的问题根源）

### 修复代码
```java
// 精确的修复代码，直接可使用
```

### 影响分析
（修复可能影响的其他代码）

### 防御建议
（如何预防此类问题）

"""
    return prompt


def build_upstream_analysis_prompt(
    error_info: Dict[str, Any],
    method_info: Dict[str, Any],
    call_chain: Dict[str, Any]
) -> str:
    """针对上游参数/数据问题的分析"""
    exception_message = error_info.get("exception_message", "")
    
    method_name = method_info.get("name", "Unknown") if method_info else "Unknown"
    method_params = method_info.get("params", "") if method_info else ""
    called_by = call_chain.get("called_by", []) if call_chain else []
    
    prompt = f"""## 上游问题分析

**错误消息**: {exception_message}

## 当前方法信息

- **方法名**: {method_name}
- **参数**: {method_params}

## 调用该方法的上游方法:
{called_by[:5] if called_by else "无"}

## 分析要求

请分析这个错误是否是上游（调用方）导致的问题：

### 1. 参数分析
- 当前方法的参数是否可能为空或不合法
- 调用方传入的参数是否符合方法要求

### 2. 上游排查建议
- 需要检查哪些上游方法
- 需要检查哪些参数

### 3. 修复方案
- 是在当前方法增加校验，还是要求上游修正

请按以下格式回复：

### 问题定位
（是上游问题还是本方法问题）

### 根因分析
（详细说明）

### 修复建议
（具体步骤）

### 上游需要修改的地方
（如有）

"""
    return prompt


def build_downstream_analysis_prompt(
    error_info: Dict[str, Any],
    method_info: Dict[str, Any],
    call_chain: Dict[str, Any]
) -> str:
    """针对下游调用问题的分析"""
    exception_message = error_info.get("exception_message", "")
    
    method_name = method_info.get("name", "Unknown") if method_info else "Unknown"
    calls = call_chain.get("calls", []) if call_chain else []
    
    prompt = f"""## 下游问题分析

**错误消息**: {exception_message}

## 当前方法信息

- **方法名**: {method_name}

## 该方法调用的下游方法:
{calls[:10] if calls else "无"}

## 分析要求

请分析这个错误是否是下游服务导致的问题：

### 1. 下游调用分析
- 哪个下游调用可能失败
- 下游返回了什么错误

### 2. 下游问题处理
- 如何处理下游异常
- 是否需要重试

### 3. 修复方案
- 增加异常处理
- 增加重试机制
- 增加降级处理

### 4. 最佳实践
- 下游调用注意事项

请按以下格式回复：

### 问题定位
（是否是下游问题）

### 根因分析
（详细说明）

### 修复建议
（具体步骤）

### 防御建议
（如何处理下游异常）

"""
    return prompt


def build_db_analysis_prompt(
    error_info: Dict[str, Any],
    method_info: Dict[str, Any],
    call_chain: Dict[str, Any]
) -> str:
    """针对数据库问题的分析"""
    exception_message = error_info.get("exception_message", "")
    
    method_name = method_info.get("name", "Unknown") if method_info else "Unknown"
    
    prompt = f"""## 数据库问题分析

**错误消息**: {exception_message}

## 当前方法信息

- **方法名**: {method_name}

## 分析要求

请分析这个数据库相关的错误：

### 1. SQL分析
- SQL语句是否正确
- 查询条件是否有误

### 2. 数据分析
- 数据是否存在
- 数据状态是否正确
- 是否有并发问题

### 3. 连接分析
- 数据库连接是否正常
- 是否有连接泄漏

### 4. 修复方案

请按以下格式回复：

### 问题定位
（SQL问题还是数据问题）

### 根因分析
（详细说明）

### 修复建议
（具体步骤）

### 优化建议
（如何避免类似问题）

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

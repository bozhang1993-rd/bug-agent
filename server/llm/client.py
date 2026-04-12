from typing import List, Dict, Any, Optional
import requests
from .config import config


class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or config.llm_provider
        self.llm_config = config.llm_config
        
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json"
        }
        
        api_key = self.llm_config.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        return headers

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if self.provider == "deepseek":
            return self._deepseek_chat(messages, **kwargs)
        elif self.provider == "glm":
            return self._glm_chat(messages, **kwargs)
        elif self.provider == "minimax":
            return self._minimax_chat(messages, **kwargs)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    def _deepseek_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        base_url = self.llm_config.get("base_url", "https://api.deepseek.com/v1")
        model = self.llm_config.get("model", "deepseek-coder")
        
        url = f"{base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        response = requests.post(url, json=payload, headers=self._get_headers(), timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _glm_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        base_url = self.llm_config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        model = self.llm_config.get("model", "glm-4")
        
        url = f"{base_url}/chat/completions"
        
        glm_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            glm_messages.append({"role": role, "content": content})
        
        payload = {
            "model": model,
            "messages": glm_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        response = requests.post(url, json=payload, headers=self._get_headers(), timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _minimax_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        base_url = self.llm_config.get("base_url", "https://api.minimax.chat/v1")
        model = self.llm_config.get("model", "MiniMax-M2.1")
        
        url = f"{base_url}/text/chatcompletion_v2"
        
        minimax_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            minimax_messages.append({"role": role, "content": content})
        
        payload = {
            "model": model,
            "messages": minimax_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        response = requests.post(url, json=payload, headers=self._get_headers(), timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def analyze_error(
        self, 
        error_info: dict, 
        code_context: str,
        error_type: str
    ) -> Dict[str, Any]:
        from .prompt import build_analysis_prompt
        
        prompt = build_analysis_prompt(error_info, code_context, error_type)
        
        messages = [
            {"role": "system", "content": "你是一个资深的Java开发工程师，擅长分析代码Bug并给出修复方案。"},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat(messages)
        
        return self._parse_analysis_result(result)

    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        analysis = {
            "root_cause": "",
            "fix_suggestion": "",
            "fix_code": "",
            "confidence": 0.8
        }
        
        lines = result.split("\n")
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if "根因" in line or "原因" in line or "Root Cause" in line.upper():
                current_section = "root_cause"
                continue
            elif "建议" in line or "修复" in line or "Solution" in line.upper():
                current_section = "fix_suggestion"
                continue
            elif "代码" in line or "Code" in line.upper():
                current_section = "fix_code"
                continue
            
            if current_section and line:
                if current_section == "root_cause":
                    analysis["root_cause"] += line + "\n"
                elif current_section == "fix_suggestion":
                    analysis["fix_suggestion"] += line + "\n"
                elif current_section == "fix_code":
                    analysis["fix_code"] += line + "\n"
        
        analysis["root_cause"] = analysis["root_cause"].strip()
        analysis["fix_suggestion"] = analysis["fix_suggestion"].strip()
        analysis["fix_code"] = analysis["fix_code"].strip()
        
        return analysis


def get_llm_client() -> LLMClient:
    return LLMClient()

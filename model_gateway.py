"""Runtime model gateway for local and API providers.

The gateway is deliberately small and dependency-free. Secrets come only from
environment variables. Agent roles choose a ModelSpec; this module performs
the provider call and returns observable metadata plus the model response.
"""
from __future__ import annotations
import json, os, urllib.request, urllib.error
from typing import Any, Mapping, Optional

class ModelGatewayError(RuntimeError):
    pass

def _urlopen_json(url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout: int = 90) -> Mapping[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json", **dict(headers)}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise ModelGatewayError(f"HTTP {exc.code} en model provider: {detail}") from exc
    except Exception as exc:
        raise ModelGatewayError(str(exc)) from exc

def _messages(prompt: str, context: Mapping[str, Any]) -> list[dict[str, str]]:
    system = str(context.get("system_prompt") or "Eres un agente especializado de Praxis Suite. Devuelve una respuesta verificable y estructurada.")
    return [{"role":"system","content":system},{"role":"user","content":prompt}]

def invoke_model(model_spec, prompt: str, context: Optional[Mapping[str, Any]] = None, *, timeout: int = 90) -> dict[str, Any]:
    context = dict(context or {})
    provider = str(model_spec.provider).lower()
    model = str(model_spec.model)
    messages = _messages(prompt, context)
    if provider == "ollama":
        base = os.getenv(model_spec.endpoint_env or "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        data = _urlopen_json(base + "/api/chat", {"model":model,"messages":messages,"stream":False}, {}, timeout)
        content = ((data.get("message") or {}).get("content") or "").strip()
        return {"content":content,"provider":provider,"model":model}
    if provider in {"groq","openrouter"}:
        base_default = "https://api.groq.com/openai/v1" if provider == "groq" else "https://openrouter.ai/api/v1"
        base = os.getenv(model_spec.endpoint_env or ("GROQ_BASE_URL" if provider=="groq" else "OPENROUTER_BASE_URL"), base_default).rstrip("/")
        key = os.getenv(model_spec.api_key_env or ("GROQ_API_KEY" if provider=="groq" else "OPENROUTER_API_KEY"), "").strip()
        if not key:
            raise ModelGatewayError(f"No está configurada la clave para {provider}")
        data = _urlopen_json(base + "/chat/completions", {"model":model,"messages":messages}, {"Authorization":"Bearer "+key}, timeout)
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return {"content":content,"provider":provider,"model":model}
    if provider == "gemini":
        base = os.getenv(model_spec.endpoint_env or "GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        key = os.getenv(model_spec.api_key_env or "GEMINI_API_KEY", "").strip()
        if not key:
            raise ModelGatewayError("No está configurada GEMINI_API_KEY")
        url = f"{base}/models/{model}:generateContent?key={key}"
        data = _urlopen_json(url, {"contents":[{"role":"user","parts":[{"text":prompt}]}]}, {}, timeout)
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        content = "".join(str(p.get("text") or "") for p in parts).strip()
        return {"content":content,"provider":provider,"model":model}
    raise ModelGatewayError(f"Proveedor no soportado: {provider}")

def build_agent_prompt(task, context: Mapping[str, Any]) -> str:
    allowed = {}
    for key in task.inputs:
        if key in context:
            value = context[key]
            text_value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
            allowed[key] = text_value[:30000]
    return (
        f"Agente: {task.agent_id}\n"
        f"Objetivo: ejecutar su responsabilidad contractual.\n"
        f"Salidas esperadas: {', '.join(task.outputs)}\n"
        f"Puertas de calidad: {', '.join(task.quality_gates)}\n"
        "Contexto de entrada:\n" + json.dumps(allowed, ensure_ascii=False, indent=2)
    )

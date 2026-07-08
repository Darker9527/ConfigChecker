# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass


@dataclass
class AIDecision:
    status: str
    evidence: str
    reason: str
    suggestion: str


def _normalize_status(value: str) -> str:
    value = (value or '').strip()
    if value in {'通过', '合规', 'pass', 'PASS'}:
        return '通过'
    if value in {'未通过', '不合规', 'fail', 'FAIL'}:
        return '未通过'
    if value in {'不适用', 'N/A', 'na'}:
        return '不适用'
    return '需复核'


def ai_check_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    config_text: str,
    baseline_name: str,
    baseline_content: str,
    evidence_hint: str = '',
    timeout: int = 60,
    retries: int = 2,
) -> AIDecision:
    """调用 OpenAI-compatible Chat Completions API，返回结构化判定。

    仅使用标准库 urllib，避免重建版必须依赖 openai SDK。
    """
    if not base_url or not api_key or not model:
        raise RuntimeError('AI 配置不完整：需要 ai_base_url、ai_api_key、ai_model')
    url = base_url.rstrip('/') + '/chat/completions'
    config_excerpt = config_text[:24000]
    prompt = f"""
你是等保合规配置核查专家。请根据基线要求审查设备配置，输出严格 JSON，不要输出 Markdown。

基线名称：{baseline_name}
基线要求：{baseline_content}
规则引擎初步证据：{evidence_hint}

配置文本：
{config_excerpt}

JSON 字段：
- status: 只能是 通过、未通过、不适用、需复核
- evidence: 引用配置行或说明缺失证据
- reason: 判定原因
- suggestion: 整改建议
""".strip()
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': '你只输出合法 JSON。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.1,
    }
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST',
    )
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode('utf-8', errors='replace')
            obj = json.loads(body)
            content = obj['choices'][0]['message']['content'].strip()
            break
        except Exception as e:
            last_error = e
            if attempt >= retries:
                raise
            time.sleep(min(2 ** attempt, 8))
    else:
        raise RuntimeError(f'AI 请求失败：{last_error!r}')
    if content.startswith('```'):
        content = content.strip('`')
        if content.lower().startswith('json'):
            content = content[4:].strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        return AIDecision(status='需复核', evidence='', reason=f'AI 未返回合法 JSON：{content[:500]}', suggestion='请人工复核或调整模型提示词。')
    return AIDecision(
        status=_normalize_status(result.get('status', '需复核')),
        evidence=str(result.get('evidence', '')),
        reason=str(result.get('reason', '')),
        suggestion=str(result.get('suggestion', '')),
    )

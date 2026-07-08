# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RuleDecision:
    status: str
    evidence: str
    reason: str
    suggestion: str


def split_terms(text: str) -> list[str]:
    parts = re.split(r'[，,；;、\s]+', text or '')
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def find_evidence(config_text: str, terms: list[str], max_lines: int = 8) -> list[str]:
    lines = config_text.splitlines()
    hits = []
    lowered_terms = [t.lower() for t in terms]
    for i, line in enumerate(lines, start=1):
        low = line.lower()
        if any(t in low for t in lowered_terms):
            hits.append(f'L{i}: {line.strip()}')
            if len(hits) >= max_lines:
                break
    return hits


def rule_check(config_text: str, baseline_content: str, cmd: str | None = None) -> RuleDecision:
    """轻量规则判定：先找 cmd/基线关键词证据，再给出需人工复核的结论。

    这是保守模式：找到证据不直接等于合规；未找到证据判为未通过。
    """
    terms = []
    if cmd:
        terms.extend(split_terms(cmd.replace('|', ' ')))
    terms.extend(split_terms(baseline_content)[:20])
    # 常见配置关键词优先
    preferred = [
        'ssh', 'https', 'telnet', 'snmp', 'ntp', 'syslog', 'logging', 'info-center',
        'acl', 'aaa', 'password', 'cipher', 'audit', 'ssl', 'tls', 'ips', 'av',
        'PermitRootLogin', 'TMOUT', 'pam_faillock', 'validate_password'
    ]
    terms = preferred + terms
    hits = find_evidence(config_text, terms)
    if hits:
        return RuleDecision(
            status='需复核',
            evidence='\n'.join(hits),
            reason='配置中发现相关证据，需结合判定标准人工/AI复核是否完全满足。',
            suggestion='对照基线判定标准逐项确认当前值、范围、例外和留存记录。',
        )
    return RuleDecision(
        status='未通过',
        evidence='未在配置文本中发现相关关键配置。',
        reason='缺少可用于证明该项合规的配置证据。',
        suggestion='按基线要求补充配置；如该项不适用，应在报告中说明设备型号、版本和不适用原因。',
    )

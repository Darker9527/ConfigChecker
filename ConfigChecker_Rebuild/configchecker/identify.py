# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

RULES = [
    ('防火墙', 'Fortinet', ['fortigate', 'config firewall policy', 'set srcintf', 'set dstintf']),
    ('防火墙', '华为', ['security-policy', 'firewall zone', 'display security-policy']),
    ('交换机', '华为', ['sysname', 'stelnet server enable', 'user-interface vty', 'info-center']),
    ('交换机', 'H3C', ['line vty', 'local-user', 'display current-configuration', 'comware']),
    ('交换机', '思科', ['show running-config', 'line vty', 'enable secret', 'transport input']),
    ('路由器', '华为', ['ospf', 'bgp', 'ip route-static', 'user-interface vty']),
    ('数据库', 'MySQL', ['mysqld', 'validate_password', 'bind-address', 'mysql.user']),
    ('数据库', 'PostgreSQL', ['pg_hba.conf', 'postgresql.conf', 'listen_addresses', 'password_encryption']),
    ('中间件', '通用', ['nginx.conf', 'server_tokens', 'ssl_protocols', 'access_log']),
    ('中间件', '通用', ['server.xml', 'tomcat', 'catalina', 'ajp']),
    ('操作系统', 'CentOS', ['/etc/ssh/sshd_config', 'pam_faillock', 'login.defs', 'system-auth']),
    ('操作系统', 'Microsoft', ['auditpol', 'secedit', 'net accounts', 'Terminal Server']),
]


def identify_text(text: str) -> tuple[str, str, list[tuple[int, str, str]]]:
    low = text.lower()
    scores = []
    for devtype, brand, terms in RULES:
        score = sum(1 for t in terms if t.lower() in low)
        if score:
            scores.append((score, devtype, brand))
    scores.sort(reverse=True)
    if scores:
        score, devtype, brand = scores[0]
        return devtype, brand, scores[:5]
    return '网络设备', '通用', []


def identify_file(path: str | Path) -> tuple[str, str, list[tuple[int, str, str]]]:
    text = Path(path).read_text(encoding='utf-8', errors='ignore')[:200000]
    return identify_text(text)

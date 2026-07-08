# ConfigChecker基线核查工具

一个 ConfigChecker 工作流基线核查工具的开源可维护版本：基于文本配置文件 + SQLite 基线库 + AI/规则判定 + HTML 报告。

## 功能

- 设备类型/品牌/基线库管理
- 文本配置文件导入检查
- 规则关键词判定与 AI 判定接口预留
- 批量检查任务
- HTML 报告输出
- 基线 CSV 导入导出
- 数据库初始化与健康检查

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m configchecker init-db
python -m configchecker import-baseline examples/baseline_seed.csv
python -m configchecker check examples/huawei.cfg --devtype 交换机 --brand 华为 --name demo
```

报告默认输出到：

```text
reports/
```

## 命令

```bash
python -m configchecker init-db
python -m configchecker summary
python -m configchecker import-baseline baseline.csv
python -m configchecker export-baseline baseline.export.csv
python -m configchecker check config.txt --devtype 防火墙 --brand 通用 --name task1
python -m configchecker check config.txt --devtype 防火墙 --brand 通用 --name task1 --mode hybrid --format html,csv,xlsx,docx,pdf,xml,remediation
python -m configchecker batch configs/ --devtype 网络设备 --brand 通用 --name batch1 --workers 4 --format html,csv
python -m configchecker migrate-original ../ConfigChecker_v2.0.0/ConfigChecker_v2.0.0/data.db
python -m configchecker config list
python -m configchecker config set ai_base_url https://api.example.com/v1
python -m configchecker config set ai_model your-model
python -m configchecker config set ai_api_key your-key
python -m configchecker tasks
python -m configchecker task-detail 1
python -m configchecker remediation 1

# 启动 GUI
python -m configchecker.gui

# 启动 Web API
uvicorn configchecker.api:app --reload --host 0.0.0.0 --port 8000
```

## CSV 字段

```text
name,descr,reference,content,devtype,brand,chktype,cmd,risk,level
```


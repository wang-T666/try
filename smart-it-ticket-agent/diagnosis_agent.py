from typing import Dict, Any, List
from .base_agent import BaseAgent
import random


class DiagnosisAgent(BaseAgent):
    """诊断Agent - 负责根因分析和长链推理"""
    
    def __init__(self, config: Dict[str, Any], llm_client=None):
        super().__init__(name="DiagnosisAgent", config=config, llm_client=llm_client)
        self.known_issues = {
            "disk_full": {
                "symptoms": ["磁盘空间不足", "disk full", "no space left"],
                "checks": ["df -h", "du -sh /*", "journalctl --disk-usage"],
                "fix": "cleanup_logs",
                "confidence": 0.95
            },
            "service_crash": {
                "symptoms": ["服务无响应", "service down", "connection refused"],
                "checks": ["systemctl status", "tail -n 100 /var/log/syslog", "dmesg | tail"],
                "fix": "restart_service",
                "confidence": 0.90
            },
            "memory_leak": {
                "symptoms": ["内存使用率高", "OOM", "out of memory"],
                "checks": ["free -m", "ps aux --sort=-%mem | head", "top -b -n1"],
                "fix": "restart_service",
                "confidence": 0.85
            }
        }
        
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行诊断流程（长链推理）"""
        ticket = context.get("ticket", {})
        router_result = context.get("router_result", {})
        
        diagnostic_chain = []
        findings = []
        
        # Step 1: 收集症状信息
        symptoms = self._collect_symptoms(ticket)
        self.log_step("症状收集", ticket.get("id"), symptoms)
        diagnostic_chain.append({"step": 1, "action": "收集症状", "result": symptoms})
        
        # Step 2: 查询监控系统（模拟）
        monitoring_data = self._query_monitoring(ticket.get("server_ip", ""))
        self.log_step("查询监控", ticket.get("server_ip"), monitoring_data)
        diagnostic_chain.append({"step": 2, "action": "查询监控", "result": monitoring_data})
        
        # Step 3: 查询日志系统（模拟）
        log_data = self._query_logs(ticket.get("server_ip", ""), 
                                     symptoms)
        self.log_step("查询日志", "最近1小时日志", f"找到{len(log_data)}条相关日志")
        diagnostic_chain.append({"step": 3, "action": "查询日志", "result": log_data})
        
        # Step 4: 长链推理 - 根因分析
        root_cause = self._chain_reasoning(symptoms, monitoring_data, log_data)
        self.log_step("根因分析", "推理链", root_cause)
        diagnostic_chain.append({"step": 4, "action": "根因分析", "result": root_cause})
        
        # Step 5: 生成修复方案
        if root_cause and root_cause.get("fix_strategy"):
            fix_plan = self._generate_fix_plan(root_cause)
            self.log_step("修复方案", root_cause["root_cause"], fix_plan)
            diagnostic_chain.append({"step": 5, "action": "修复方案", "result": fix_plan})
        else:
            fix_plan = {"action": "manual_escalation", "reason": "未能确定根因"}
            diagnostic_chain.append({"step": 5, "action": "升级人工", "result": fix_plan})
        
        return {
            "ticket_id": ticket.get("id"),
            "symptoms": symptoms,
            "root_cause": root_cause,
            "fix_plan": fix_plan,
            "diagnostic_chain": diagnostic_chain,
            "findings": findings,
            "confidence": root_cause.get("confidence", 0) if root_cause else 0
        }
    
    def _collect_symptoms(self, ticket: Dict) -> List[str]:
        """收集症状"""
        symptoms = []
        description = ticket.get("description", "").lower()
        
        for issue_id, issue_info in self.known_issues.items():
            for symptom in issue_info["symptoms"]:
                if symptom.lower() in description:
                    symptoms.append(symptom)
        
        if not symptoms:
            symptoms.append("未明确症状，需要进一步排查")
        
        return symptoms
    
    def _query_monitoring(self, server_ip: str) -> Dict:
        """查询监控系统（模拟API调用）"""
        # 模拟返回监控数据
        metrics = {
            "cpu_usage": random.randint(30, 95),
            "memory_usage": random.randint(40, 98),
            "disk_usage": random.randint(50, 99),
            "network_io": f"{random.randint(100, 900)}MB/s",
            "active_connections": random.randint(10, 500)
        }
        return {"server": server_ip, "metrics": metrics, "timestamp": "2024-01-15T10:30:00Z"}
    
    def _query_logs(self, server_ip: str, symptoms: List[str]) -> List[Dict]:
        """查询日志系统（模拟ELK查询）"""
        log_entries = [
            {"level": "ERROR", "message": "磁盘写入失败: No space left on device", "count": 15},
            {"level": "WARN", "message": "内存使用率达到85%", "count": 8},
            {"level": "ERROR", "message": "服务健康检查失败: timeout", "count": 3},
        ]
        return log_entries[:random.randint(1, 3)]
    
    def _chain_reasoning(self, symptoms: List[str], 
                         monitoring: Dict, 
                         logs: List[Dict]) -> Dict:
        """长链推理：基于多步证据得出根因"""
        reasoning_steps = []
        
        # 推理步骤1：分析症状与已知问题的匹配度
        matches = {}
        for issue_id, issue_info in self.known_issues.items():
            match_count = sum(1 for s in symptoms 
                            if any(symptom in s.lower() for symptom in issue_info["symptoms"]))
            if match_count > 0:
                matches[issue_id] = match_count / len(issue_info["symptoms"])
        
        reasoning_steps.append(f"症状匹配度: {matches}")
        
        # 推理步骤2：结合监控数据验证
        if monitoring.get("metrics", {}).get("disk_usage", 0) > 85:
            if "disk_full" in matches:
                matches["disk_full"] = min(matches["disk_full"] + 0.2, 1.0)
                reasoning_steps.append("监控显示磁盘使用率>85%，支持磁盘满假设")
        
        if monitoring.get("metrics", {}).get("memory_usage", 0) > 90:
            if "memory_leak" in matches:
                matches["memory_leak"] = min(matches["memory_leak"] + 0.2, 1.0)
                reasoning_steps.append("监控显示内存使用率>90%，支持内存泄漏假设")
        
        # 推理步骤3：结合日志证据
        for log in logs:
            if "disk" in log.get("message", "").lower():
                if "disk_full" in matches:
                    matches["disk_full"] = min(matches["disk_full"] + 0.1, 1.0)
                    reasoning_steps.append(f"日志证据: {log['message']}")
        
        # 推理步骤4：得出最终结论
        if not matches:
            return {"root_cause": "未知", "confidence": 0, "fix_strategy": None, 
                    "reasoning": reasoning_steps}
        
        best_match = max(matches, key=matches.get)
        confidence = matches[best_match]
        issue = self.known_issues[best_match]
        
        return {
            "root_cause": best_match,
            "confidence": min(confidence, 1.0),
            "fix_strategy": issue["fix"],
            "diagnostic_checks": issue["checks"],
            "reasoning": reasoning_steps
        }
    
    def _generate_fix_plan(self, root_cause: Dict) -> Dict:
        """生成修复方案"""
        strategies = {
            "cleanup_logs": {
                "action": "cleanup_disk",
                "commands": [
                    "journalctl --vacuum-size=500M",
                    "find /var/log -type f -name '*.log' -mtime +7 -exec gzip {} \\;",
                    "docker system prune -af"
                ],
                "estimated_time": "5分钟",
                "risk_level": "低"
            },
            "restart_service": {
                "action": "restart_service",
                "commands": [
                    "systemctl restart nginx",
                    "supervisorctl restart all"
                ],
                "estimated_time": "2分钟",
                "risk_level": "中"
            }
        }
        
        strategy_name = root_cause.get("fix_strategy", "")
        return strategies.get(strategy_name, {
            "action": "manual_intervention",
            "reason": "无预设修复方案"
        })
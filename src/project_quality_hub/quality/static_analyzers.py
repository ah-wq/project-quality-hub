"""Static analysis integrations for Project Quality Hub."""

from __future__ import annotations

import json
import os
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class StaticAnalysisResult:
    """静态分析结果"""
    tool_name: str
    file_path: str
    line: int
    column: int
    severity: str  # 'error', 'warning', 'info'
    rule_id: str
    message: str
    category: str  # 'security', 'style', 'performance', 'type', 'complexity'
    suggestion: Optional[str] = None
    auto_fixable: bool = False

class StaticAnalyzer(ABC):
    """静态分析工具基类"""
    
    @abstractmethod
    def analyze_file(self, file_path: str) -> List[StaticAnalysisResult]:
        """分析单个文件"""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """检查工具是否可用"""
        pass

class ESLintAnalyzer(StaticAnalyzer):
    """ESLint JavaScript/TypeScript分析器"""
    
    def __init__(self):
        self.supported_extensions = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
        self.config = {
            "env": {
                "browser": True,
                "es2021": True,
                "node": True
            },
            "extends": [
                "eslint:recommended"
            ],
            "parserOptions": {
                "ecmaVersion": 12,
                "sourceType": "module"
            },
            "rules": {
                "no-unused-vars": "warn",
                "no-console": "warn", 
                "complexity": ["warn", 15],
                "max-depth": ["warn", 4],
                "max-len": ["warn", {"code": 120}],
                "no-magic-numbers": "warn",
                "prefer-const": "error",
                "no-var": "error"
            }
        }
    
    def analyze_file(self, file_path: str) -> List[StaticAnalysisResult]:
        """使用ESLint分析文件"""
        if not self._is_supported_file(file_path) or not self.is_available():
            return []
            
        try:
            # 创建临时配置文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
                json.dump(self.config, config_file)
                config_path = config_file.name
                
            # 运行ESLint
            cmd = [
                'npx', 'eslint', 
                '--config', config_path,
                '--format', 'json',
                file_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            # 清理临时文件
            os.unlink(config_path)
            
            if result.stdout:
                return self._parse_eslint_output(result.stdout, file_path)
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("ESLint分析失败 %s: %s", file_path, exc)
        return []
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查是否为支持的文件类型"""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def _parse_eslint_output(self, output: str, file_path: str) -> List[StaticAnalysisResult]:
        """解析ESLint输出"""
        results = []
        
        try:
            data = json.loads(output)
            
            for file_result in data:
                for message in file_result.get('messages', []):
                    severity = self._map_severity(message.get('severity', 1))
                    category = self._categorize_rule(message.get('ruleId', ''))
                    
                    result = StaticAnalysisResult(
                        tool_name='ESLint',
                        file_path=file_path,
                        line=message.get('line', 1),
                        column=message.get('column', 1),
                        severity=severity,
                        rule_id=message.get('ruleId', 'unknown'),
                        message=message.get('message', ''),
                        category=category,
                        suggestion=self._get_suggestion(message.get('ruleId', '')),
                        auto_fixable=message.get('fix') is not None
                    )
                    results.append(result)
                    
        except json.JSONDecodeError:
            logger.warning("解析ESLint输出失败: %s", output)
            
        return results
    
    def _map_severity(self, severity: int) -> str:
        """映射严重程度"""
        return 'error' if severity == 2 else 'warning'
    
    def _categorize_rule(self, rule_id: str) -> str:
        """规则分类"""
        security_rules = ['no-eval', 'no-implied-eval', 'no-unsafe-negation']
        performance_rules = ['no-unnecessary-call', 'prefer-spread']
        style_rules = ['indent', 'quotes', 'semi', 'space-before-function-paren']
        complexity_rules = ['complexity', 'max-depth', 'max-len']
        
        if rule_id in security_rules:
            return 'security'
        elif rule_id in performance_rules:
            return 'performance'
        elif rule_id in style_rules:
            return 'style'
        elif rule_id in complexity_rules:
            return 'complexity'
        else:
            return 'general'
    
    def _get_suggestion(self, rule_id: str) -> Optional[str]:
        """获取修复建议"""
        suggestions = {
            'no-unused-vars': 'Remove unused variables or prefix with underscore',
            'no-console': 'Replace console.log with proper logging framework',
            'complexity': 'Break down function into smaller functions',
            'max-depth': 'Reduce nesting depth by extracting functions',
            'prefer-const': 'Use const for variables that are not reassigned',
            'no-var': 'Use let or const instead of var'
        }
        return suggestions.get(rule_id)
    
    def is_available(self) -> bool:
        """检查ESLint是否可用"""
        try:
            result = subprocess.run(['npx', 'eslint', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

class BanditAnalyzer(StaticAnalyzer):
    """Bandit Python安全分析器"""
    
    def __init__(self):
        self.supported_extensions = {'.py'}
        
    def analyze_file(self, file_path: str) -> List[StaticAnalysisResult]:
        """使用Bandit分析Python文件安全问题"""
        if not self._is_supported_file(file_path) or not self.is_available():
            return []
            
        try:
            cmd = [
                'bandit', 
                '-f', 'json',
                '-ll',  # 低和高级别问题
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                return self._parse_bandit_output(result.stdout, file_path)
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("Bandit分析失败 %s: %s", file_path, exc)
        return []
    
    def _is_supported_file(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def _parse_bandit_output(self, output: str, file_path: str) -> List[StaticAnalysisResult]:
        """解析Bandit输出"""
        results = []
        
        try:
            data = json.loads(output)
            
            for issue in data.get('results', []):
                severity = self._map_bandit_severity(
                    issue.get('issue_severity', 'LOW'),
                    issue.get('issue_confidence', 'LOW')
                )
                
                result = StaticAnalysisResult(
                    tool_name='Bandit',
                    file_path=file_path,
                    line=issue.get('line_number', 1),
                    column=issue.get('col_offset', 1),
                    severity=severity,
                    rule_id=issue.get('test_id', 'unknown'),
                    message=issue.get('issue_text', ''),
                    category='security',
                    suggestion=self._get_bandit_suggestion(issue.get('test_id', '')),
                    auto_fixable=False
                )
                results.append(result)
                
        except json.JSONDecodeError:
            logger.warning("解析Bandit输出失败: %s", output)
            
        return results
    
    def _map_bandit_severity(self, severity: str, confidence: str) -> str:
        """映射Bandit严重程度"""
        if severity == 'HIGH' and confidence == 'HIGH':
            return 'error'
        elif severity == 'MEDIUM' or confidence == 'HIGH':
            return 'warning'
        else:
            return 'info'
    
    def _get_bandit_suggestion(self, test_id: str) -> Optional[str]:
        """获取安全修复建议"""
        suggestions = {
            'B101': 'Use assert only for debugging, not for data validation',
            'B102': 'Use proper exception handling instead of exec',
            'B103': 'Set appropriate file permissions (avoid 0o777)',
            'B108': 'Use a proper tmp directory with appropriate permissions',
            'B301': 'Use pickle alternatives like json for untrusted data',
            'B601': 'Validate and sanitize shell command parameters',
            'B602': 'Use subprocess with shell=False for better security'
        }
        return suggestions.get(test_id)
    
    def is_available(self) -> bool:
        """检查Bandit是否可用"""
        try:
            result = subprocess.run(['bandit', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

class PyFlakesAnalyzer(StaticAnalyzer):
    """PyFlakes Python语法检查器"""
    
    def __init__(self):
        self.supported_extensions = {'.py'}
        
    def analyze_file(self, file_path: str) -> List[StaticAnalysisResult]:
        """使用PyFlakes分析Python文件"""
        if not self._is_supported_file(file_path) or not self.is_available():
            return []
            
        try:
            cmd = ['python', '-m', 'pyflakes', file_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                return self._parse_pyflakes_output(result.stdout, file_path)
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("PyFlakes分析失败 %s: %s", file_path, exc)
        return []
    
    def _is_supported_file(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def _parse_pyflakes_output(self, output: str, file_path: str) -> List[StaticAnalysisResult]:
        """解析PyFlakes输出"""
        results = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
                
            # PyFlakes输出格式: file:line: message
            parts = line.split(':', 2)
            if len(parts) >= 3:
                try:
                    line_num = int(parts[1])
                    message = parts[2].strip()
                    
                    result = StaticAnalysisResult(
                        tool_name='PyFlakes',
                        file_path=file_path,
                        line=line_num,
                        column=1,
                        severity=self._determine_severity(message),
                        rule_id='pyflakes',
                        message=message,
                        category=self._categorize_message(message),
                        suggestion=self._get_pyflakes_suggestion(message),
                        auto_fixable=False
                    )
                    results.append(result)
                    
                except ValueError:
                    continue
                    
        return results
    
    def _determine_severity(self, message: str) -> str:
        """根据消息确定严重程度"""
        if 'undefined name' in message or 'imported but unused' in message:
            return 'warning'
        elif 'redefined' in message:
            return 'info'
        else:
            return 'warning'
    
    def _categorize_message(self, message: str) -> str:
        """消息分类"""
        if 'imported but unused' in message or 'undefined name' in message:
            return 'style'
        elif 'redefined' in message:
            return 'general'
        else:
            return 'general'
    
    def _get_pyflakes_suggestion(self, message: str) -> Optional[str]:
        """获取修复建议"""
        if 'imported but unused' in message:
            return 'Remove unused import or use __all__ to export'
        elif 'undefined name' in message:
            return 'Define the variable or fix the spelling'
        elif 'redefined' in message:
            return 'Use different variable names to avoid redefinition'
        return None
    
    def is_available(self) -> bool:
        """检查PyFlakes是否可用"""
        try:
            result = subprocess.run(['python', '-m', 'pyflakes', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return 'pyflakes' in result.stdout.lower()
        except Exception:
            return False

class MultiLanguageStaticAnalyzer:
    """多语言静态分析器集成"""
    
    def __init__(self):
        self.analyzers = {
            'javascript': ESLintAnalyzer(),
            'typescript': ESLintAnalyzer(), 
            'python': [BanditAnalyzer(), PyFlakesAnalyzer()]
        }
        self.language_mapping = {
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.mjs': 'javascript',
            '.cjs': 'javascript',
            '.py': 'python'
        }
        
    def analyze_file(self, file_path: str) -> List[StaticAnalysisResult]:
        """分析文件 - 自动选择合适的分析器"""
        if not os.path.exists(file_path):
            return []
            
        file_extension = Path(file_path).suffix.lower()
        language = self.language_mapping.get(file_extension)
        
        if not language:
            return []
            
        results = []
        analyzers = self.analyzers.get(language, [])
        
        # 处理单个分析器或分析器列表
        if not isinstance(analyzers, list):
            analyzers = [analyzers]
            
        for analyzer in analyzers:
            try:
                analyzer_results = analyzer.analyze_file(file_path)
                results.extend(analyzer_results)
            except Exception as exc:
                logger.warning("分析器 %s 失败: %s", analyzer.__class__.__name__, exc)
                
        return results
    
    def get_available_analyzers(self) -> Dict[str, List[str]]:
        """获取可用的分析器"""
        available = {}
        
        for language, analyzers in self.analyzers.items():
            if not isinstance(analyzers, list):
                analyzers = [analyzers]
                
            available_list = []
            for analyzer in analyzers:
                if analyzer.is_available():
                    available_list.append(analyzer.__class__.__name__)
                    
            if available_list:
                available[language] = available_list
                
        return available
    
    def install_missing_tools(self) -> Dict[str, str]:
        """安装缺失的工具"""
        install_commands = {
            'ESLint': 'npm install -g eslint',
            'Bandit': 'pip install bandit',
            'PyFlakes': 'pip install pyflakes'
        }
        
        missing = {}
        for language, analyzers in self.analyzers.items():
            if not isinstance(analyzers, list):
                analyzers = [analyzers]
                
            for analyzer in analyzers:
                if not analyzer.is_available():
                    tool_name = analyzer.__class__.__name__.replace('Analyzer', '')
                    missing[tool_name] = install_commands.get(tool_name, 'Unknown installation method')
                    
        return missing

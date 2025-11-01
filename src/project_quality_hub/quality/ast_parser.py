"""AST parser and code metrics utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class CodeMetrics:
    """代码质量指标"""
    file_path: str
    language: str
    lines_of_code: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    function_count: int
    class_count: int
    max_nesting_depth: int
    long_functions: List[str]  # 超过50行的函数
    duplicated_code_blocks: List[str]
    maintainability_index: float  # 0-100
    technical_debt_minutes: int

@dataclass
class QualityIssue:
    """质量问题"""
    file_path: str
    line: int
    column: int
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'complexity', 'style', 'security', 'performance'
    message: str
    suggestion: str
    auto_fixable: bool

class TreeSitterParser:
    """Tree-sitter AST解析器"""
    
    def __init__(self):
        self.supported_languages = {
            '.js': 'javascript',
            '.jsx': 'javascript', 
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.py': 'python',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp'
        }
        
        # 复杂度权重配置
        self.complexity_weights = {
            'if_statement': 1,
            'while_statement': 1, 
            'for_statement': 1,
            'switch_statement': 1,
            'try_statement': 1,
            'catch_clause': 1,
            'conditional_expression': 1,
            'logical_and': 1,
            'logical_or': 1
        }
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """检测文件语言"""
        suffix = Path(file_path).suffix.lower()
        return self.supported_languages.get(suffix)
    
    def parse_file(self, file_path: str) -> Optional[CodeMetrics]:
        """解析单个文件"""
        if not os.path.exists(file_path):
            return None
            
        language = self.detect_language(file_path)
        if not language:
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return self._analyze_code(file_path, content, language)
            
        except Exception as e:
            logger.warning("解析文件失败 %s: %s", file_path, e)
            return None
    
    def _analyze_code(self, file_path: str, content: str, language: str) -> CodeMetrics:
        """分析代码内容"""
        lines = content.split('\n')
        loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        
        # 基础指标计算
        metrics = CodeMetrics(
            file_path=file_path,
            language=language,
            lines_of_code=loc,
            cyclomatic_complexity=self._calculate_cyclomatic_complexity(content, language),
            cognitive_complexity=self._calculate_cognitive_complexity(content, language),
            function_count=self._count_functions(content, language),
            class_count=self._count_classes(content, language),
            max_nesting_depth=self._calculate_max_nesting_depth(content, language),
            long_functions=self._find_long_functions(content, language),
            duplicated_code_blocks=self._find_duplicated_code(content),
            maintainability_index=0.0,  # 后续计算
            technical_debt_minutes=0    # 后续计算
        )
        
        # 计算维护性指数
        metrics.maintainability_index = self._calculate_maintainability_index(metrics)
        
        # 计算技术债务
        metrics.technical_debt_minutes = self._calculate_technical_debt(metrics)
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, content: str, language: str) -> int:
        """计算循环复杂度"""
        complexity = 1  # 基础复杂度
        
        # 简化版本：基于关键词计数
        complexity_keywords = {
            'python': ['if', 'elif', 'while', 'for', 'try', 'except', 'and', 'or'],
            'javascript': ['if', 'else if', 'while', 'for', 'switch', 'case', 'try', 'catch', '&&', '||'],
            'typescript': ['if', 'else if', 'while', 'for', 'switch', 'case', 'try', 'catch', '&&', '||'],
            'java': ['if', 'else if', 'while', 'for', 'switch', 'case', 'try', 'catch', '&&', '||']
        }
        
        keywords = complexity_keywords.get(language, [])
        for keyword in keywords:
            complexity += content.count(keyword)
            
        return min(complexity, 50)  # 最大复杂度限制
    
    def _calculate_cognitive_complexity(self, content: str, language: str) -> int:
        """计算认知复杂度 (更注重人类理解难度)"""
        cognitive = 0
        nesting_level = 0
        
        lines = content.split('\n')
        for line in lines:
            stripped = line.strip()
            
            # 计算嵌套层级
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'try']):
                if stripped.endswith(':') or stripped.endswith('{'):
                    nesting_level += 1
                    cognitive += nesting_level  # 嵌套越深，认知负担越重
                    
            # 减少嵌套层级
            if stripped in ['}', 'end', 'endif'] or stripped.startswith('except'):
                nesting_level = max(0, nesting_level - 1)
                
        return min(cognitive, 100)
    
    def _count_functions(self, content: str, language: str) -> int:
        """统计函数数量"""
        function_patterns = {
            'python': ['def ', 'async def '],
            'javascript': ['function ', '=> ', 'async function'],
            'typescript': ['function ', '=> ', 'async function'],
            'java': ['public ', 'private ', 'protected '],
        }
        
        patterns = function_patterns.get(language, [])
        count = 0
        for pattern in patterns:
            count += content.count(pattern)
            
        return count
    
    def _count_classes(self, content: str, language: str) -> int:
        """统计类数量"""
        class_patterns = {
            'python': ['class '],
            'javascript': ['class '],
            'typescript': ['class ', 'interface '],
            'java': ['class ', 'interface ', 'enum ']
        }
        
        patterns = class_patterns.get(language, [])
        count = 0
        for pattern in patterns:
            count += content.count(pattern)
            
        return count
    
    def _calculate_max_nesting_depth(self, content: str, language: str) -> int:
        """计算最大嵌套深度"""
        max_depth = 0
        current_depth = 0
        
        lines = content.split('\n')
        for line in lines:
            stripped = line.strip()
            
            # 增加深度的模式
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'try', 'def', 'class']):
                if stripped.endswith(':') or stripped.endswith('{'):
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                    
            # 减少深度的模式  
            elif stripped in ['}', 'end'] or (language == 'python' and len(line) - len(line.lstrip()) < 4):
                current_depth = max(0, current_depth - 1)
                
        return max_depth
    
    def _find_long_functions(self, content: str, language: str) -> List[str]:
        """找出长函数 (>50行)"""
        long_functions = []
        lines = content.split('\n')
        current_function = None
        function_start = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 检测函数开始
            if language == 'python' and stripped.startswith('def '):
                if current_function and (i - function_start) > 50:
                    long_functions.append(f"{current_function} ({i - function_start} lines)")
                current_function = stripped.split('(')[0].replace('def ', '')
                function_start = i
                
            elif language in ['javascript', 'typescript'] and 'function ' in stripped:
                if current_function and (i - function_start) > 50:
                    long_functions.append(f"{current_function} ({i - function_start} lines)")
                current_function = self._extract_function_name(stripped)
                function_start = i
                
        return long_functions
    
    def _extract_function_name(self, line: str) -> str:
        """提取函数名"""
        if 'function ' in line:
            parts = line.split('function ')[1].split('(')[0].strip()
            return parts
        return "anonymous"
    
    def _find_duplicated_code(self, content: str) -> List[str]:
        """检测重复代码块 (简化版)"""
        duplicates = []
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # 查找连续相同的代码块 (>3行)
        for i in range(len(lines) - 3):
            block = lines[i:i+3]
            for j in range(i+3, len(lines) - 2):
                if lines[j:j+3] == block:
                    duplicates.append(f"Lines {i+1}-{i+3} duplicated at {j+1}-{j+3}")
                    
        return duplicates[:5]  # 限制数量
    
    def _calculate_maintainability_index(self, metrics: CodeMetrics) -> float:
        """计算维护性指数 (0-100, 100最好)"""
        # Microsoft维护性指数公式的简化版本
        volume = metrics.lines_of_code * 0.23  # 代码量惩罚
        complexity_penalty = metrics.cyclomatic_complexity * 3.2
        cognitive_penalty = metrics.cognitive_complexity * 2.5
        
        base_score = 100
        penalty = volume + complexity_penalty + cognitive_penalty
        
        if metrics.long_functions:
            penalty += len(metrics.long_functions) * 5
            
        if metrics.duplicated_code_blocks:
            penalty += len(metrics.duplicated_code_blocks) * 10
            
        score = max(0, base_score - penalty)
        return min(100, score)
    
    def _calculate_technical_debt(self, metrics: CodeMetrics) -> int:
        """计算技术债务 (分钟)"""
        debt = 0
        
        # 复杂度债务
        if metrics.cyclomatic_complexity > 10:
            debt += (metrics.cyclomatic_complexity - 10) * 15
            
        # 长函数债务
        debt += len(metrics.long_functions) * 30
        
        # 重复代码债务
        debt += len(metrics.duplicated_code_blocks) * 45
        
        # 嵌套深度债务
        if metrics.max_nesting_depth > 4:
            debt += (metrics.max_nesting_depth - 4) * 20
            
        return debt

class QualityAnalyzer:
    """代码质量分析器"""
    
    def __init__(self):
        self.parser = TreeSitterParser()
        self.issues = []
        
    def analyze_file(self, file_path: str) -> Tuple[Optional[CodeMetrics], List[QualityIssue]]:
        """分析单个文件"""
        metrics = self.parser.parse_file(file_path)
        issues = []
        
        if metrics:
            issues = self._generate_quality_issues(metrics)
            
        return metrics, issues
    
    def _generate_quality_issues(self, metrics: CodeMetrics) -> List[QualityIssue]:
        """基于指标生成质量问题"""
        issues = []
        
        # 复杂度问题
        if metrics.cyclomatic_complexity > 15:
            issues.append(QualityIssue(
                file_path=metrics.file_path,
                line=1,
                column=1,
                severity='warning',
                category='complexity',
                message=f'Cyclomatic complexity is {metrics.cyclomatic_complexity} (threshold: 15)',
                suggestion='Consider breaking down large functions into smaller ones',
                auto_fixable=False
            ))
            
        if metrics.cognitive_complexity > 25:
            issues.append(QualityIssue(
                file_path=metrics.file_path,
                line=1,
                column=1,
                severity='warning',
                category='complexity', 
                message=f'Cognitive complexity is {metrics.cognitive_complexity} (threshold: 25)',
                suggestion='Reduce nesting depth and simplify logic flow',
                auto_fixable=False
            ))
            
        # 长函数问题
        for long_func in metrics.long_functions:
            issues.append(QualityIssue(
                file_path=metrics.file_path,
                line=1,
                column=1,
                severity='info',
                category='style',
                message=f'Long function detected: {long_func}',
                suggestion='Consider extracting smaller functions for better readability',
                auto_fixable=False
            ))
            
        # 重复代码问题
        for duplicate in metrics.duplicated_code_blocks:
            issues.append(QualityIssue(
                file_path=metrics.file_path,
                line=1,
                column=1,
                severity='warning',
                category='style',
                message=f'Duplicated code: {duplicate}',
                suggestion='Extract common code into reusable functions',
                auto_fixable=False
            ))
            
        # 维护性问题
        if metrics.maintainability_index < 30:
            issues.append(QualityIssue(
                file_path=metrics.file_path,
                line=1,
                column=1,
                severity='error',
                category='maintainability',
                message=f'Low maintainability index: {metrics.maintainability_index:.1f}',
                suggestion='Refactor to improve code structure and reduce complexity',
                auto_fixable=False
            ))
            
        return issues

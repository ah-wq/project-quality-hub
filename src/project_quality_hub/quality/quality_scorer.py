"""Intelligent quality scoring utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .ast_parser import CodeMetrics, QualityIssue
from .static_analyzers import StaticAnalysisResult

logger = logging.getLogger(__name__)

class QualityCategory(Enum):
    """质量分类"""
    MAINTAINABILITY = "maintainability"
    RELIABILITY = "reliability" 
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    COMPLEXITY = "complexity"

@dataclass
class QualityScore:
    """质量评分详情"""
    total_score: float  # 总分 0-100
    category_scores: Dict[QualityCategory, float] = field(default_factory=dict)
    grade: str = ""  # A+, A, B, C, D, F
    technical_debt_hours: float = 0.0
    priority_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """计算等级"""
        if self.total_score >= 95:
            self.grade = "A+"
        elif self.total_score >= 90:
            self.grade = "A"
        elif self.total_score >= 80:
            self.grade = "B"
        elif self.total_score >= 70:
            self.grade = "C"
        elif self.total_score >= 60:
            self.grade = "D"
        else:
            self.grade = "F"

@dataclass
class ScoringWeights:
    """评分权重配置"""
    # 主要维度权重 (总和为1.0)
    maintainability: float = 0.25
    reliability: float = 0.25
    security: float = 0.20
    performance: float = 0.15
    style: float = 0.10
    complexity: float = 0.05
    
    # 子指标权重
    cyclomatic_complexity_weight: float = 0.4
    cognitive_complexity_weight: float = 0.3
    nesting_depth_weight: float = 0.3
    
    # 惩罚权重
    error_penalty: float = 20.0
    warning_penalty: float = 5.0
    info_penalty: float = 1.0
    
    # 奖励权重  
    good_practices_bonus: float = 5.0
    comprehensive_tests_bonus: float = 10.0

class IntelligentQualityScorer:
    """智能质量评分器"""
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        
        # 质量阈值配置
        self.thresholds = {
            'cyclomatic_complexity': {'good': 5, 'acceptable': 10, 'bad': 15},
            'cognitive_complexity': {'good': 10, 'acceptable': 20, 'bad': 30},
            'nesting_depth': {'good': 3, 'acceptable': 4, 'bad': 6},
            'function_length': {'good': 20, 'acceptable': 50, 'bad': 100},
            'maintainability_index': {'good': 80, 'acceptable': 60, 'bad': 40},
            'technical_debt_minutes': {'good': 30, 'acceptable': 120, 'bad': 480}
        }
        
        # 最佳实践模式
        self.good_practices = {
            'typescript': ['strict type checking', 'interfaces', 'generics'],
            'python': ['type hints', 'docstrings', 'list comprehensions'],
            'javascript': ['const usage', 'arrow functions', 'destructuring']
        }
    
    def calculate_quality_score(
        self, 
        metrics: CodeMetrics, 
        static_results: List[StaticAnalysisResult],
        quality_issues: List[QualityIssue]
    ) -> QualityScore:
        """计算综合质量评分"""
        
        # 初始化分类评分
        category_scores = {}
        
        # 1. 维护性评分
        category_scores[QualityCategory.MAINTAINABILITY] = self._calculate_maintainability_score(
            metrics, static_results
        )
        
        # 2. 可靠性评分
        category_scores[QualityCategory.RELIABILITY] = self._calculate_reliability_score(
            metrics, static_results, quality_issues
        )
        
        # 3. 安全性评分
        category_scores[QualityCategory.SECURITY] = self._calculate_security_score(
            static_results
        )
        
        # 4. 性能评分
        category_scores[QualityCategory.PERFORMANCE] = self._calculate_performance_score(
            metrics, static_results
        )
        
        # 5. 风格评分
        category_scores[QualityCategory.STYLE] = self._calculate_style_score(
            static_results
        )
        
        # 6. 复杂度评分
        category_scores[QualityCategory.COMPLEXITY] = self._calculate_complexity_score(
            metrics
        )
        
        # 计算加权总分
        total_score = self._calculate_weighted_total(category_scores)
        
        # 应用奖励和惩罚
        total_score = self._apply_bonuses_and_penalties(
            total_score, metrics, static_results
        )
        
        # 生成评分详情
        quality_score = QualityScore(
            total_score=max(0, min(100, total_score)),
            category_scores=category_scores,
            technical_debt_hours=metrics.technical_debt_minutes / 60.0,
            priority_issues=self._identify_priority_issues(quality_issues, static_results),
            recommendations=self._generate_recommendations(metrics, static_results),
            strengths=self._identify_strengths(metrics, category_scores)
        )
        
        return quality_score
    
    def _calculate_maintainability_score(
        self, 
        metrics: CodeMetrics, 
        static_results: List[StaticAnalysisResult]
    ) -> float:
        """计算维护性评分"""
        mi_score = (
            float(metrics.maintainability_index)
            if hasattr(metrics, "maintainability_index")
            else float(self._estimate_maintainability_index(metrics))
        )
        base_score = max(0.0, min(100.0, mi_score))
        
        # 复杂度惩罚
        complexity_penalty = 0
        if metrics.cyclomatic_complexity > self.thresholds['cyclomatic_complexity']['acceptable']:
            complexity_penalty += (metrics.cyclomatic_complexity - 10) * 2
        
        if metrics.cognitive_complexity > self.thresholds['cognitive_complexity']['acceptable']:
            complexity_penalty += (metrics.cognitive_complexity - 20) * 1.5
        
        # 长函数惩罚
        long_function_penalty = len(metrics.long_functions) * 5
        
        # 重复代码惩罚
        duplicate_penalty = len(metrics.duplicated_code_blocks) * 8
        
        # 静态分析问题惩罚
        static_penalty = sum(
            3 for result in static_results 
            if result.category == 'style' and result.severity == 'warning'
        )
        
        final_score = (
            base_score
            - complexity_penalty
            - long_function_penalty
            - duplicate_penalty
            - static_penalty
        )
        return max(0, min(100, final_score))
    
    def _calculate_reliability_score(
        self, 
        metrics: CodeMetrics,
        static_results: List[StaticAnalysisResult],
        quality_issues: List[QualityIssue]
    ) -> float:
        """计算可靠性评分"""
        base_score = 100.0
        
        # 错误严重程度惩罚
        error_penalty = sum(
            self.weights.error_penalty for result in static_results 
            if result.severity == 'error'
        )
        
        warning_penalty = sum(
            self.weights.warning_penalty for result in static_results 
            if result.severity == 'warning'
        )
        
        # 质量问题惩罚
        quality_penalty = sum(
            15 if issue.severity == 'error' else 
            8 if issue.severity == 'warning' else 3
            for issue in quality_issues
        )
        
        # 复杂度可靠性影响
        complexity_reliability_impact = 0
        if metrics.cyclomatic_complexity > 20:
            complexity_reliability_impact = (metrics.cyclomatic_complexity - 20) * 1.5
        
        final_score = base_score - error_penalty - warning_penalty - quality_penalty - complexity_reliability_impact
        return max(0, min(100, final_score))
    
    def _calculate_security_score(self, static_results: List[StaticAnalysisResult]) -> float:
        """计算安全性评分"""
        base_score = 100.0
        
        security_issues = [r for r in static_results if r.category == 'security']
        
        # 安全问题惩罚
        security_penalty = 0
        for issue in security_issues:
            if issue.severity == 'error':
                security_penalty += 25  # 严重安全问题
            elif issue.severity == 'warning':
                security_penalty += 10  # 中等安全问题
            else:
                security_penalty += 3   # 轻微安全问题
        
        # 特定安全规则的额外惩罚
        high_risk_patterns = ['B601', 'B602', 'B301']  # Bandit高风险规则
        for issue in security_issues:
            if issue.rule_id in high_risk_patterns:
                security_penalty += 15
        
        final_score = base_score - security_penalty
        return max(0, min(100, final_score))
    
    def _calculate_performance_score(
        self, 
        metrics: CodeMetrics,
        static_results: List[StaticAnalysisResult]
    ) -> float:
        """计算性能评分"""
        base_score = 100.0
        
        # 性能相关问题惩罚
        performance_issues = [r for r in static_results if r.category == 'performance']
        performance_penalty = len(performance_issues) * 5
        
        # 复杂度对性能的影响
        complexity_performance_impact = 0
        if metrics.cyclomatic_complexity > 15:
            complexity_performance_impact = (metrics.cyclomatic_complexity - 15) * 2
        
        # 嵌套深度影响性能
        nesting_impact = 0
        if metrics.max_nesting_depth > 4:
            nesting_impact = (metrics.max_nesting_depth - 4) * 3
        
        # 长函数可能影响性能
        long_function_impact = len(metrics.long_functions) * 2
        
        final_score = base_score - performance_penalty - complexity_performance_impact - nesting_impact - long_function_impact
        return max(0, min(100, final_score))
    
    def _calculate_style_score(self, static_results: List[StaticAnalysisResult]) -> float:
        """计算风格评分"""
        base_score = 100.0
        
        style_issues = [r for r in static_results if r.category == 'style']
        
        # 风格问题惩罚 (相对轻微)
        style_penalty = 0
        for issue in style_issues:
            if issue.severity == 'error':
                style_penalty += 8
            elif issue.severity == 'warning':
                style_penalty += 3
            else:
                style_penalty += 1
        
        final_score = base_score - style_penalty
        return max(0, min(100, final_score))
    
    def _calculate_complexity_score(self, metrics: CodeMetrics) -> float:
        """计算复杂度评分"""
        # 循环复杂度评分
        cc_score = self._score_by_threshold(
            metrics.cyclomatic_complexity,
            self.thresholds['cyclomatic_complexity']
        ) * self.weights.cyclomatic_complexity_weight
        
        # 认知复杂度评分
        cog_score = self._score_by_threshold(
            metrics.cognitive_complexity,
            self.thresholds['cognitive_complexity']
        ) * self.weights.cognitive_complexity_weight
        
        # 嵌套深度评分
        nest_score = self._score_by_threshold(
            metrics.max_nesting_depth,
            self.thresholds['nesting_depth']
        ) * self.weights.nesting_depth_weight
        
        # 加权平均
        weighted_score = (cc_score + cog_score + nest_score) / (
            self.weights.cyclomatic_complexity_weight +
            self.weights.cognitive_complexity_weight +
            self.weights.nesting_depth_weight
        )
        
        return max(0, min(100, weighted_score * 100))
    
    def _score_by_threshold(self, value: float, thresholds: Dict[str, float]) -> float:
        """根据阈值计算评分 (0-1)"""
        if value <= thresholds['good']:
            return 1.0
        elif value <= thresholds['acceptable']:
            # 线性插值
            ratio = (value - thresholds['good']) / (thresholds['acceptable'] - thresholds['good'])
            return 1.0 - (ratio * 0.3)  # good到acceptable降30%
        elif value <= thresholds['bad']:
            ratio = (value - thresholds['acceptable']) / (thresholds['bad'] - thresholds['acceptable'])
            return 0.7 - (ratio * 0.5)  # acceptable到bad再降50%
        else:
            # 超过bad阈值，继续下降
            excess_ratio = min(2.0, (value - thresholds['bad']) / thresholds['bad'])
            return max(0.0, 0.2 - (excess_ratio * 0.2))
    
    def _calculate_weighted_total(self, category_scores: Dict[QualityCategory, float]) -> float:
        """计算加权总分"""
        total = 0.0
        total += category_scores[QualityCategory.MAINTAINABILITY] * self.weights.maintainability
        total += category_scores[QualityCategory.RELIABILITY] * self.weights.reliability
        total += category_scores[QualityCategory.SECURITY] * self.weights.security
        total += category_scores[QualityCategory.PERFORMANCE] * self.weights.performance
        total += category_scores[QualityCategory.STYLE] * self.weights.style
        total += category_scores[QualityCategory.COMPLEXITY] * self.weights.complexity
        
        return total
    
    def _apply_bonuses_and_penalties(
        self, 
        base_score: float, 
        metrics: CodeMetrics, 
        static_results: List[StaticAnalysisResult]
    ) -> float:
        """应用奖励和惩罚"""
        adjusted_score = base_score
        
        # 最佳实践奖励
        if self._has_good_practices(metrics):
            adjusted_score += self.weights.good_practices_bonus
        
        # 类型安全奖励 (TypeScript, Python type hints)
        if self._has_type_safety(metrics, static_results):
            adjusted_score += 3
        
        # 文档完整性奖励
        if self._has_good_documentation(metrics):
            adjusted_score += 2
        
        return adjusted_score
    
    def _has_good_practices(self, metrics: CodeMetrics) -> bool:
        """检查是否遵循最佳实践"""
        # 简化版本：基于复杂度和结构
        return (
            metrics.cyclomatic_complexity <= 10 and
            metrics.max_nesting_depth <= 3 and
            len(metrics.long_functions) == 0
        )
    
    def _has_type_safety(self, metrics: CodeMetrics, static_results: List[StaticAnalysisResult]) -> bool:
        """检查类型安全"""
        # 简化版本：基于文件扩展名和静态分析结果
        has_types = (
            metrics.language in ['typescript', 'java', 'rust', 'go'] or
            (metrics.language == 'python' and any('type' in r.message.lower() for r in static_results))
        )
        return has_types
    
    def _has_good_documentation(self, metrics: CodeMetrics) -> bool:
        """检查文档质量"""
        # 简化版本：基于函数数量和复杂度的合理性
        if metrics.function_count == 0:
            return True  # 简单脚本无需过多文档
        
        # 复杂函数应该有文档
        return len(metrics.long_functions) == 0 or metrics.function_count > 5
    
    def _identify_priority_issues(
        self, 
        quality_issues: List[QualityIssue],
        static_results: List[StaticAnalysisResult]
    ) -> List[str]:
        """识别优先修复的问题"""
        priority_issues = []
        
        # 安全问题最高优先级
        security_issues = [r for r in static_results if r.category == 'security' and r.severity == 'error']
        for issue in security_issues[:3]:  # 最多3个
            priority_issues.append(f"🚨 Security: {issue.message}")
        
        # 复杂度问题
        complexity_issues = [i for i in quality_issues if i.category == 'complexity' and i.severity == 'error']
        for issue in complexity_issues[:2]:  # 最多2个
            priority_issues.append(f"⚡ Complexity: {issue.message}")
        
        # 可靠性问题
        reliability_issues = [r for r in static_results if r.severity == 'error'][:2]
        for issue in reliability_issues:
            priority_issues.append(f"⚠️  Reliability: {issue.message}")
        
        return priority_issues
    
    def _generate_recommendations(
        self, 
        metrics: CodeMetrics,
        static_results: List[StaticAnalysisResult]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 复杂度建议
        if metrics.cyclomatic_complexity > 15:
            recommendations.append(
                f"Reduce cyclomatic complexity from {metrics.cyclomatic_complexity} to ≤10 by extracting functions"
            )
        
        if metrics.cognitive_complexity > 25:
            recommendations.append(
                f"Simplify logic to reduce cognitive complexity from {metrics.cognitive_complexity} to ≤15"
            )
        
        # 结构建议
        if len(metrics.long_functions) > 0:
            recommendations.append(
                f"Break down {len(metrics.long_functions)} long functions into smaller, focused functions"
            )
        
        if len(metrics.duplicated_code_blocks) > 0:
            recommendations.append(
                "Extract common code patterns into reusable functions to eliminate duplication"
            )
        
        # 安全建议
        security_issues = [r for r in static_results if r.category == 'security']
        if security_issues:
            recommendations.append(
                f"Address {len(security_issues)} security issues detected by static analysis"
            )
        
        return recommendations[:5]  # 最多5个建议
    
    def _identify_strengths(
        self, 
        metrics: CodeMetrics,
        category_scores: Dict[QualityCategory, float]
    ) -> List[str]:
        """识别代码优势"""
        strengths = []
        
        # 基于分类评分识别优势
        for category, score in category_scores.items():
            if score >= 85:
                strengths.append(f"Excellent {category.value}")
        
        # 具体优势
        if metrics.cyclomatic_complexity <= 5:
            strengths.append("Low complexity - easy to understand")
        
        if metrics.max_nesting_depth <= 2:
            strengths.append("Minimal nesting - clean structure")
        
        if len(metrics.long_functions) == 0:
            strengths.append("Well-sized functions")
        
        if len(metrics.duplicated_code_blocks) == 0:
            strengths.append("No code duplication")
        
        return strengths
    
    def calculate_comprehensive_score(
        self, 
        metrics: CodeMetrics, 
        static_results: List[StaticAnalysisResult],
        quality_issues: List[QualityIssue] = None
    ) -> QualityScore:
        """计算综合质量评分 (兼容方法)
        
        这是 calculate_quality_score 的别名方法，为了向后兼容
        """
        if quality_issues is None:
            quality_issues = []
            
        return self.calculate_quality_score(metrics, static_results, quality_issues)
    
    def _estimate_maintainability_index(self, metrics: CodeMetrics) -> float:
        """估算维护性指数"""
        # 简化的维护性指数计算
        base_score = 100
        
        # 复杂度惩罚
        complexity_penalty = metrics.cyclomatic_complexity * 2
        cognitive_penalty = metrics.cognitive_complexity * 1.5
        
        # 代码量惩罚
        loc_penalty = max(0, (metrics.lines_of_code - 100) * 0.1)
        
        # 结构问题惩罚
        structure_penalty = len(metrics.long_functions) * 5 + len(metrics.duplicated_code_blocks) * 8
        
        score = base_score - complexity_penalty - cognitive_penalty - loc_penalty - structure_penalty
        return max(0, min(100, score))

"""SuperClaude ProjectMind System - 智能项目记忆系统

核心功能:
1. 项目知识图谱构建和维护
2. 代码依赖关系深度分析  
3. 项目上下文智能理解
4. 代码变更影响智能预测
5. 项目记忆持久化存储

让Claude获得量子级别的项目理解能力，远超其他Claude Code
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class CodeEntity:
    """代码实体 - 函数、类、变量等"""
    name: str
    entity_type: str  # 'function', 'class', 'variable', 'import', 'interface'
    file_path: str
    line_number: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    complexity_score: float = 0.0
    usage_count: int = 0
    last_modified: datetime = field(default_factory=datetime.now)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)


@dataclass 
class FileNode:
    """文件节点"""
    file_path: str
    language: str
    size_bytes: int
    line_count: int
    last_modified: datetime
    file_hash: str
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)  
    entities: List[CodeEntity] = field(default_factory=list)
    risk_score: float = 0.0
    change_frequency: int = 0


@dataclass
class ProjectContext:
    """项目上下文信息"""
    project_root: str
    project_name: str
    framework_type: str  # 'react', 'vue', 'node', 'python', 'java', etc.
    main_language: str
    architecture_pattern: str  # 'mvc', 'mvvm', 'microservices', 'monorepo'
    build_system: str  # 'webpack', 'vite', 'gradle', 'maven', etc.
    package_manager: str  # 'npm', 'yarn', 'pip', 'maven'
    version: str
    last_analysis: datetime = field(default_factory=datetime.now)
    total_files: int = 0
    total_lines: int = 0
    complexity_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class DependencyRelation:
    """依赖关系"""
    from_entity: str
    to_entity: str
    relation_type: str  # 'imports', 'calls', 'extends', 'implements', 'uses'
    strength: float  # 依赖强度 0-1
    file_path: str
    line_number: int


class ProjectKnowledgeGraph:
    """项目知识图谱 - ProjectMind的核心"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).absolute()
        self.graph = nx.DiGraph()  # 有向图存储依赖关系
        self.files: Dict[str, FileNode] = {}
        self.entities: Dict[str, CodeEntity] = {}
        self.context: Optional[ProjectContext] = None
        self.change_history: List[Dict] = []
        
        # 支持的文件类型和语言
        self.supported_extensions = {
            '.py': 'python',
            '.js': 'javascript', 
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp'
        }
        
        # 框架识别模式
        self.framework_patterns = {
            'react': ['react', 'jsx', 'tsx', 'package.json'],
            'vue': ['vue', '@vue', 'vue-cli'],
            'angular': ['@angular', 'angular.json'],
            'node': ['package.json', 'node_modules'],
            'django': ['django', 'manage.py', 'settings.py'],
            'flask': ['flask', 'app.py'],
            'spring': ['spring', 'pom.xml', '@SpringBootApplication'],
            'next': ['next', 'next.config.js']
        }
    
    def analyze_project(self, max_files: int = 1000) -> ProjectContext:
        """完整项目分析 - 构建知识图谱"""
        logger.info("🧠 ProjectMind 开始深度项目分析...")
        
        # 1. 项目基础信息分析
        context = self._analyze_project_context()
        self.context = context
        
        # 2. 文件扫描和分析
        files_analyzed = self._scan_and_analyze_files(max_files)
        logger.info("📁 分析了 %s 个文件", files_analyzed)
        
        # 3. 构建依赖关系图
        dependency_count = self._build_dependency_graph()
        logger.info("🔗 构建了 %s 个依赖关系", dependency_count)
        
        # 4. 实体关系分析
        entities = self._analyze_entity_relationships()
        logger.info("🧩 识别了 %s 个代码实体", entities)
        
        # 5. 风险评估和复杂度分析
        self._calculate_risk_scores()
        
        # 6. 更新上下文统计
        self._update_context_statistics()
        
        logger.info(
            "✅ ProjectMind 分析完成! 项目: %s | 框架: %s | 语言: %s | 文件: %s | 代码行: %s",
            context.project_name,
            context.framework_type,
            context.main_language,
            context.total_files,
            context.total_lines,
        )
        
        return context

    def analyze_changed_files(self, changed_files):
        """仅分析指定的已更改文件，用于增量分析"""
        logger.info("🧠 ProjectMind 增量分析 %s 个更改的文件...", len(changed_files))
        
        # 1. 如果没有现有上下文，先进行基础项目分析
        if not self.context:
            self.context = self._analyze_project_context()
        
        # 2. 仅分析更改的文件
        files_analyzed = 0
        for file_path in changed_files:
            full_path = Path(self.project_root) / file_path
            if full_path.exists() and full_path.is_file():
                file_node = self._analyze_single_file(full_path)
                if file_node:
                    # 🔧 修复：将分析的文件添加到self.files中
                    self.files[file_node.file_path] = file_node
                    files_analyzed += 1
        
        logger.info("📁 增量分析了 %s 个更改文件", files_analyzed)
        
        # 3. 更新依赖关系（仅涉及更改文件的部分）
        dependency_count = self._build_dependency_graph()
        logger.info("🔗 更新依赖关系数量: %s", dependency_count)
        
        # 4. 更新统计信息
        self._update_context_statistics()
        
        logger.info("✅ ProjectMind 增量分析完成!")
        return self.context

    def _analyze_project_context(self) -> ProjectContext:
        """分析项目上下文信息"""
        project_name = self.project_root.name
        
        # 检测框架类型
        framework_type = self._detect_framework_type()
        
        # 检测主要编程语言
        main_language = self._detect_main_language()
        
        # 检测架构模式
        architecture_pattern = self._detect_architecture_pattern()
        
        # 检测构建系统
        build_system = self._detect_build_system()
        
        # 检测包管理器
        package_manager = self._detect_package_manager()
        
        # 获取版本信息
        version = self._get_project_version()
        
        return ProjectContext(
            project_root=str(self.project_root),
            project_name=project_name,
            framework_type=framework_type,
            main_language=main_language,
            architecture_pattern=architecture_pattern,
            build_system=build_system,
            package_manager=package_manager,
            version=version
        )
    
    def _detect_framework_type(self) -> str:
        """检测框架类型"""
        # 检查package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    
                    if 'react' in deps or 'next' in deps:
                        return 'next' if 'next' in deps else 'react'
                    elif '@vue/core' in deps or 'vue' in deps:
                        return 'vue'
                    elif '@angular/core' in deps:
                        return 'angular'
                    elif 'express' in deps:
                        return 'express'
                    else:
                        return 'node'
            except Exception:
                pass
        
        # 检查Python项目
        if (self.project_root / "requirements.txt").exists() or (self.project_root / "pyproject.toml").exists():
            return 'python'
        
        # 检查Java项目
        if (self.project_root / "pom.xml").exists():
            return 'spring'
        
        # 检查Go项目
        if (self.project_root / "go.mod").exists():
            return 'go'
        
        return 'unknown'
    
    def _detect_main_language(self) -> str:
        """检测主要编程语言"""
        language_count = defaultdict(int)
        
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                language = self.supported_extensions[file_path.suffix]
                language_count[language] += 1
        
        if language_count:
            return max(language_count, key=language_count.get)
        
        return 'unknown'
    
    def _detect_architecture_pattern(self) -> str:
        """检测架构模式"""
        # 检查目录结构
        dirs = [d.name.lower() for d in self.project_root.iterdir() if d.is_dir()]
        
        if 'packages' in dirs or 'apps' in dirs:
            return 'monorepo'
        elif 'src' in dirs and ('components' in dirs or 'views' in dirs):
            return 'spa'
        elif 'controllers' in dirs and 'models' in dirs and 'views' in dirs:
            return 'mvc'
        elif 'services' in dirs and 'repositories' in dirs:
            return 'layered'
        
        return 'unknown'
    
    def _detect_build_system(self) -> str:
        """检测构建系统"""
        if (self.project_root / "webpack.config.js").exists():
            return 'webpack'
        elif (self.project_root / "vite.config.js").exists() or (self.project_root / "vite.config.ts").exists():
            return 'vite'
        elif (self.project_root / "pom.xml").exists():
            return 'maven'
        elif (self.project_root / "build.gradle").exists():
            return 'gradle'
        elif (self.project_root / "Makefile").exists():
            return 'make'
        
        return 'unknown'
    
    def _detect_package_manager(self) -> str:
        """检测包管理器"""
        if (self.project_root / "yarn.lock").exists():
            return 'yarn'
        elif (self.project_root / "package-lock.json").exists():
            return 'npm'
        elif (self.project_root / "pnpm-lock.yaml").exists():
            return 'pnpm'
        elif (self.project_root / "requirements.txt").exists():
            return 'pip'
        elif (self.project_root / "Pipfile").exists():
            return 'pipenv'
        
        return 'unknown'
    
    def _get_project_version(self) -> str:
        """获取项目版本"""
        # 检查package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
            except Exception:
                pass
        
        # 检查pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject, 'r') as f:
                    content = f.read()
                    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                    if version_match:
                        return version_match.group(1)
            except Exception:
                pass
        
        return '0.0.0'
    
    def _scan_and_analyze_files(self, max_files: int) -> int:
        """扫描和分析项目文件"""
        files_processed = 0
        
        # 忽略的目录
        ignore_dirs = {
            'node_modules', '.git', '__pycache__', '.pytest_cache',
            'dist', 'build', 'target', '.idea', '.vscode', 'coverage'
        }
        
        for file_path in self.project_root.rglob("*"):
            if files_processed >= max_files:
                break
                
            # 检查是否应该忽略
            if any(ignore_dir in file_path.parts for ignore_dir in ignore_dirs):
                continue
                
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                try:
                    file_node = self._analyze_single_file(file_path)
                    if file_node:
                        self.files[str(file_path)] = file_node
                        files_processed += 1
                except Exception as e:
                    logger.warning("分析文件失败 %s: %s", file_path, e)
        
        return files_processed
    
    def _analyze_single_file(self, file_path: Path) -> Optional[FileNode]:
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 文件基础信息
            stat = file_path.stat()
            file_hash = hashlib.md5(content.encode()).hexdigest()
            language = self.supported_extensions[file_path.suffix]
            
            # 行数统计
            lines = content.split('\n')
            line_count = len([line for line in lines if line.strip()])
            
            file_node = FileNode(
                file_path=str(file_path),
                language=language,
                size_bytes=stat.st_size,
                line_count=line_count,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                file_hash=file_hash
            )
            
            # 语言特定的分析
            if language == 'python':
                self._analyze_python_file(file_node, content)
            elif language in ['javascript', 'typescript']:
                self._analyze_js_file(file_node, content)
            
            return file_node
            
        except Exception as e:
            logger.warning("文件分析错误 %s: %s", file_path, e)
            return None
    
    def _analyze_python_file(self, file_node: FileNode, content: str):
        """分析Python文件"""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    entity = CodeEntity(
                        name=node.name,
                        entity_type='function',
                        file_path=file_node.file_path,
                        line_number=node.lineno,
                        signature=f"def {node.name}(...)",
                        docstring=ast.get_docstring(node)
                    )
                    file_node.entities.append(entity)
                    self.entities[f"{file_node.file_path}:{node.name}"] = entity
                
                elif isinstance(node, ast.ClassDef):
                    entity = CodeEntity(
                        name=node.name,
                        entity_type='class',
                        file_path=file_node.file_path,
                        line_number=node.lineno,
                        signature=f"class {node.name}(...)",
                        docstring=ast.get_docstring(node)
                    )
                    file_node.entities.append(entity)
                    self.entities[f"{file_node.file_path}:{node.name}"] = entity
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        file_node.imports.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_node.imports.append(node.module)
        
        except SyntaxError as e:
            logger.warning("Python语法错误 %s: %s", file_node.file_path, e)
    
    def _analyze_js_file(self, file_node: FileNode, content: str):
        """分析JavaScript/TypeScript文件 (简化版)"""
        # 简化的正则表达式分析
        
        # 查找函数定义
        function_patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*\(',
            r'(\w+)\s*:\s*function\s*\(',
            r'(\w+)\s*=>\s*'
        ]
        
        for pattern in function_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                entity = CodeEntity(
                    name=match.group(1),
                    entity_type='function',
                    file_path=file_node.file_path,
                    line_number=line_num,
                    signature=match.group(0)
                )
                file_node.entities.append(entity)
                self.entities[f"{file_node.file_path}:{match.group(1)}"] = entity
        
        # 查找类定义
        class_pattern = r'class\s+(\w+)'
        matches = re.finditer(class_pattern, content)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            entity = CodeEntity(
                name=match.group(1),
                entity_type='class',
                file_path=file_node.file_path,
                line_number=line_num,
                signature=match.group(0)
            )
            file_node.entities.append(entity)
            self.entities[f"{file_node.file_path}:{match.group(1)}"] = entity
        
        # 查找import语句
        import_patterns = [
            r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
            r'require\(["\']([^"\']+)["\']\)'
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                file_node.imports.append(match.group(1))
    
    def _build_dependency_graph(self) -> int:
        """构建依赖关系图"""
        dependency_count = 0
        
        for file_path, file_node in self.files.items():
            # 添加文件节点到图中
            self.graph.add_node(file_path, node_type='file', data=file_node)
            
            # 添加import依赖
            for import_name in file_node.imports:
                # 尝试解析到实际文件
                target_file = self._resolve_import(import_name, file_path)
                if target_file and target_file in self.files:
                    self.graph.add_edge(file_path, target_file, 
                                       relation_type='imports', 
                                       strength=0.8)
                    dependency_count += 1
            
            # 添加实体节点和关系
            for entity in file_node.entities:
                entity_key = f"{file_path}:{entity.name}"
                self.graph.add_node(entity_key, node_type='entity', data=entity)
                self.graph.add_edge(file_path, entity_key, 
                                   relation_type='contains',
                                   strength=1.0)
        
        return dependency_count
    
    def _resolve_import(self, import_name: str, from_file: str) -> Optional[str]:
        """解析import到实际文件路径"""
        # 简化版本的import解析
        if import_name.startswith('.'):
            # 相对导入
            from_dir = Path(from_file).parent
            if import_name.startswith('./'):
                import_path = from_dir / import_name[2:]
            elif import_name.startswith('../'):
                import_path = from_dir / import_name
            else:
                import_path = from_dir / import_name[1:]
            
            # 尝试不同的扩展名
            for ext in self.supported_extensions:
                potential_file = import_path.with_suffix(ext)
                if potential_file.exists():
                    return str(potential_file)
        
        return None
    
    def _analyze_entity_relationships(self) -> int:
        """分析实体关系"""
        return len(self.entities)
    
    def _calculate_risk_scores(self):
        """计算风险评分"""
        for file_path, file_node in self.files.items():
            # 基于复杂度和依赖关系计算风险
            risk_factors = []
            
            # 文件大小风险
            if file_node.size_bytes > 10000:  # >10KB
                risk_factors.append(0.3)
            
            # 行数风险
            if file_node.line_count > 500:
                risk_factors.append(0.4)
            
            # 实体数量风险
            if len(file_node.entities) > 20:
                risk_factors.append(0.3)
            
            # 依赖数量风险
            if len(file_node.imports) > 15:
                risk_factors.append(0.2)
            
            file_node.risk_score = min(1.0, sum(risk_factors))
    
    def _update_context_statistics(self):
        """更新上下文统计信息"""
        if self.context:
            self.context.total_files = len(self.files)
            self.context.total_lines = sum(f.line_count for f in self.files.values())
            
            # 复杂度分布
            complexity_levels = {'low': 0, 'medium': 0, 'high': 0, 'extreme': 0}
            for file_node in self.files.values():
                if file_node.risk_score < 0.3:
                    complexity_levels['low'] += 1
                elif file_node.risk_score < 0.6:
                    complexity_levels['medium'] += 1
                elif file_node.risk_score < 0.8:
                    complexity_levels['high'] += 1
                else:
                    complexity_levels['extreme'] += 1
            
            self.context.complexity_distribution = complexity_levels
    
    def get_entity_by_name(self, name: str) -> List[CodeEntity]:
        """根据名称查找实体"""
        return [entity for entity in self.entities.values() if name in entity.name]
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """获取文件依赖"""
        if file_path in self.graph:
            return list(self.graph.successors(file_path))
        return []
    
    def get_file_dependents(self, file_path: str) -> List[str]:
        """获取依赖此文件的其他文件"""
        if file_path in self.graph:
            return list(self.graph.predecessors(file_path))
        return []
    
    def predict_change_impact(self, file_path: str) -> Dict[str, Any]:
        """预测代码变更影响"""
        if file_path not in self.graph:
            return {'error': 'File not found in graph'}
        
        # 直接依赖
        direct_dependents = self.get_file_dependents(file_path)
        
        # 间接依赖 (2度以内)
        indirect_dependents = set()
        for dep in direct_dependents:
            indirect_dependents.update(self.get_file_dependents(dep))
        
        # 风险评估
        risk_level = 'low'
        impact_files = len(direct_dependents) + len(indirect_dependents)
        
        if impact_files > 20:
            risk_level = 'extreme'
        elif impact_files > 10:
            risk_level = 'high'
        elif impact_files > 5:
            risk_level = 'medium'
        
        return {
            'target_file': file_path,
            'direct_impact': direct_dependents,
            'indirect_impact': list(indirect_dependents),
            'total_impact_files': impact_files,
            'risk_level': risk_level,
            'recommendations': self._get_change_recommendations(risk_level, impact_files)
        }
    
    def _get_change_recommendations(self, risk_level: str, impact_files: int) -> List[str]:
        """获取变更建议"""
        recommendations = []
        
        if risk_level == 'extreme':
            recommendations.extend([
                "🚨 高风险变更：影响超过20个文件",
                "建议分阶段实施变更",
                "必须进行全面测试",
                "考虑功能开关控制发布"
            ])
        elif risk_level == 'high':
            recommendations.extend([
                "⚠️  中高风险变更：影响10-20个文件",
                "建议增加集成测试",
                "通知相关团队成员"
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                "📋 中等风险变更：影响5-10个文件",
                "建议进行回归测试"
            ])
        else:
            recommendations.append("✅ 低风险变更：影响较小")
        
        return recommendations
    
    def export_project_summary(self) -> Dict[str, Any]:
        """导出项目摘要"""
        if not self.context:
            return {'error': 'Project not analyzed'}
        
        # 获取关键统计信息
        high_risk_files = [f for f, node in self.files.items() if node.risk_score > 0.7]
        
        # 最复杂的文件
        complex_files = sorted(self.files.items(), 
                              key=lambda x: x[1].risk_score, 
                              reverse=True)[:10]
        
        # 核心实体
        core_entities = [e for e in self.entities.values() if e.usage_count > 5]
        
        return {
            'project_context': asdict(self.context),
            'statistics': {
                'total_files': len(self.files),
                'total_entities': len(self.entities),
                'dependency_relationships': self.graph.number_of_edges(),
                'high_risk_files': len(high_risk_files),
                'complexity_distribution': self.context.complexity_distribution
            },
            'high_risk_files': [{'path': f, 'risk_score': self.files[f].risk_score} 
                               for f in high_risk_files[:10]],
            'most_complex_files': [{'path': f[0], 'risk_score': f[1].risk_score, 'lines': f[1].line_count} 
                                  for f in complex_files],
            'core_entities': [{'name': e.name, 'type': e.entity_type, 'file': e.file_path} 
                             for e in core_entities[:20]]
        }

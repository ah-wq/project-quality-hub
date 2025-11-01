"""多分支项目图谱管理系统，解决同一项目多分支的知识图谱管理问题。"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .project_mind import ProjectKnowledgeGraph
from .project_memory import ProjectMemoryManager

logger = logging.getLogger(__name__)

@dataclass
class BranchContext:
    """分支上下文信息"""
    branch_name: str
    commit_hash: str
    last_commit_time: datetime
    author: str
    branch_type: str  # 'feature', 'hotfix', 'develop', 'main'
    parent_branch: Optional[str] = None
    merge_status: str = "active"  # 'active', 'merged', 'deleted'

class MultiBranchProjectMind:
    """多分支项目图谱管理器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).absolute()
        self.memory_manager = ProjectMemoryManager()
        self.current_branch = self._get_current_branch()
        self.branch_contexts: Dict[str, BranchContext] = {}

    def _get_current_branch(self) -> str:
        """获取当前Git分支名"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    def _get_commit_info(self) -> Tuple[str, datetime, str]:
        """获取当前提交信息"""
        try:
            # 获取提交hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = hash_result.stdout.strip()

            # 获取提交时间和作者
            info_result = subprocess.run(
                ["git", "log", "-1", "--format=%ct|%an"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            timestamp, author = info_result.stdout.strip().split("|")
            commit_time = datetime.fromtimestamp(int(timestamp))

            return commit_hash, commit_time, author
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown", datetime.now(), "unknown"

    def _generate_branch_project_id(self, branch_name: str) -> str:
        """生成分支特定的项目ID"""
        branch_key = f"{self.project_root}#{branch_name}"
        return hashlib.md5(branch_key.encode()).hexdigest()

    def _get_branch_type(self, branch_name: str) -> str:
        """根据分支名推断分支类型"""
        if branch_name in ['main', 'master']:
            return 'main'
        elif branch_name in ['develop', 'dev']:
            return 'develop'
        elif branch_name.startswith('feature/'):
            return 'feature'
        elif branch_name.startswith('hotfix/'):
            return 'hotfix'
        elif branch_name.startswith('release/'):
            return 'release'
        else:
            return 'other'

    def update_branch_context(self, branch_name: str = None) -> BranchContext:
        """更新分支上下文信息"""
        if branch_name is None:
            branch_name = self.current_branch

        commit_hash, commit_time, author = self._get_commit_info()
        branch_type = self._get_branch_type(branch_name)

        # 获取父分支信息（简化版）
        parent_branch = None
        if branch_type == 'feature':
            parent_branch = 'develop'
        elif branch_type == 'hotfix':
            parent_branch = 'main'

        branch_context = BranchContext(
            branch_name=branch_name,
            commit_hash=commit_hash,
            last_commit_time=commit_time,
            author=author,
            branch_type=branch_type,
            parent_branch=parent_branch
        )

        self.branch_contexts[branch_name] = branch_context
        return branch_context

    def analyze_branch_project(self, branch_name: str = None, force_update: bool = False) -> Dict[str, Any]:
        """分析特定分支的项目图谱"""
        if branch_name is None:
            branch_name = self.current_branch

        logger.info(f"🌿 分析分支项目图谱: {branch_name}")

        # 更新分支上下文
        branch_context = self.update_branch_context(branch_name)

        # 生成分支特定的项目ID
        branch_project_id = self._generate_branch_project_id(branch_name)

        # 检查是否需要更新
        if not force_update:
            existing_project = self._load_branch_project(branch_name)
            if existing_project and self._is_project_up_to_date(existing_project, branch_context):
                logger.info(f"✅ 分支 {branch_name} 的项目图谱已是最新")
                return {
                    'status': 'up_to_date',
                    'branch': branch_name,
                    'project_id': branch_project_id,
                    'last_analysis': existing_project.context.last_analysis
                }

        # 创建知识图谱
        knowledge_graph = ProjectKnowledgeGraph(str(self.project_root))
        knowledge_graph.analyze_project()

        # 更新项目上下文，添加分支信息
        if knowledge_graph.context:
            knowledge_graph.context.version = f"{branch_name}#{branch_context.commit_hash[:8]}"

        # 保存分支特定的项目图谱
        success = self._save_branch_project(branch_name, knowledge_graph, branch_context)

        if success:
            logger.info(f"✅ 分支 {branch_name} 项目图谱分析完成")
            return {
                'status': 'analyzed',
                'branch': branch_name,
                'project_id': branch_project_id,
                'files_count': len(knowledge_graph.files),
                'entities_count': len(knowledge_graph.entities),
                'analysis_time': datetime.now(),
                'commit_hash': branch_context.commit_hash,
                'branch_type': branch_context.branch_type
            }
        else:
            return {'status': 'failed', 'branch': branch_name, 'error': '保存失败'}

    def _load_branch_project(self, branch_name: str) -> Optional[ProjectKnowledgeGraph]:
        """加载特定分支的项目图谱"""
        try:
            # 临时修改项目ID生成逻辑来加载分支特定数据
            original_get_project_id = self.memory_manager.get_project_id
            self.memory_manager.get_project_id = lambda x: self._generate_branch_project_id(branch_name)

            knowledge_graph = self.memory_manager.load_project(str(self.project_root))

            # 恢复原始方法
            self.memory_manager.get_project_id = original_get_project_id

            return knowledge_graph
        except Exception as e:
            logger.warning(f"加载分支 {branch_name} 项目失败: {e}")
            return None

    def _save_branch_project(self, branch_name: str, knowledge_graph: ProjectKnowledgeGraph, branch_context: BranchContext) -> bool:
        """保存分支特定的项目图谱"""
        try:
            # 临时修改项目ID生成逻辑来保存分支特定数据
            original_get_project_id = self.memory_manager.get_project_id
            self.memory_manager.get_project_id = lambda x: self._generate_branch_project_id(branch_name)

            success = self.memory_manager.save_project(knowledge_graph)

            # 保存分支上下文信息
            if success:
                self._save_branch_context(branch_name, branch_context)

            # 恢复原始方法
            self.memory_manager.get_project_id = original_get_project_id

            return success
        except Exception as e:
            logger.error(f"保存分支 {branch_name} 项目失败: {e}")
            return False

    def _save_branch_context(self, branch_name: str, branch_context: BranchContext):
        """保存分支上下文信息"""
        context_file = self.memory_manager.storage_dir / "branch_contexts.json"

        # 加载现有上下文
        contexts = {}
        if context_file.exists():
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    contexts = json.load(f)
            except Exception:
                pass

        # 更新当前分支上下文
        project_key = str(self.project_root)
        if project_key not in contexts:
            contexts[project_key] = {}

        contexts[project_key][branch_name] = {
            'branch_name': branch_context.branch_name,
            'commit_hash': branch_context.commit_hash,
            'last_commit_time': branch_context.last_commit_time.isoformat(),
            'author': branch_context.author,
            'branch_type': branch_context.branch_type,
            'parent_branch': branch_context.parent_branch,
            'merge_status': branch_context.merge_status
        }

        # 保存更新后的上下文
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(contexts, f, indent=2, ensure_ascii=False)

    def _is_project_up_to_date(self, knowledge_graph: ProjectKnowledgeGraph, branch_context: BranchContext) -> bool:
        """检查项目图谱是否已是最新"""
        if not knowledge_graph.context:
            return False

        # 检查版本号（包含提交hash）
        expected_version = f"{branch_context.branch_name}#{branch_context.commit_hash[:8]}"
        return knowledge_graph.context.version == expected_version

    def list_branch_projects(self) -> Dict[str, Any]:
        """列出所有分支的项目图谱"""
        context_file = self.memory_manager.storage_dir / "branch_contexts.json"

        if not context_file.exists():
            return {'branches': [], 'current_branch': self.current_branch}

        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                contexts = json.load(f)

            project_key = str(self.project_root)
            if project_key not in contexts:
                return {'branches': [], 'current_branch': self.current_branch}

            branches = []
            for branch_name, context in contexts[project_key].items():
                branches.append({
                    'name': branch_name,
                    'type': context['branch_type'],
                    'last_commit': context['commit_hash'][:8],
                    'last_commit_time': context['last_commit_time'],
                    'author': context['author'],
                    'is_current': branch_name == self.current_branch
                })

            return {
                'branches': sorted(branches, key=lambda x: x['last_commit_time'], reverse=True),
                'current_branch': self.current_branch,
                'project_root': str(self.project_root)
            }

        except Exception as e:
            logger.error(f"读取分支上下文失败: {e}")
            return {'branches': [], 'current_branch': self.current_branch, 'error': str(e)}

    def switch_to_branch_analysis(self, target_branch: str) -> Dict[str, Any]:
        """切换到特定分支并进行分析"""
        logger.info(f"🔄 切换到分支: {target_branch}")

        try:
            # 检查分支是否存在
            result = subprocess.run(
                ["git", "show-ref", f"refs/heads/{target_branch}"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {'status': 'error', 'message': f'分支 {target_branch} 不存在'}

            # 切换分支
            subprocess.run(
                ["git", "checkout", target_branch],
                cwd=self.project_root,
                check=True
            )

            # 更新当前分支
            self.current_branch = target_branch

            # 分析项目
            return self.analyze_branch_project(target_branch, force_update=True)

        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f'分支切换失败: {e}'}

    def compare_branches(self, branch1: str, branch2: str) -> Dict[str, Any]:
        """比较两个分支的项目图谱差异"""
        logger.info(f"🔍 比较分支: {branch1} vs {branch2}")

        # 加载两个分支的项目图谱
        graph1 = self._load_branch_project(branch1)
        graph2 = self._load_branch_project(branch2)

        if not graph1 or not graph2:
            return {
                'status': 'error',
                'message': f'无法加载分支数据: {branch1}({bool(graph1)}) vs {branch2}({bool(graph2)})'
            }

        # 比较文件差异
        files1 = set(graph1.files.keys())
        files2 = set(graph2.files.keys())

        added_files = files2 - files1
        removed_files = files1 - files2
        common_files = files1 & files2

        # 比较实体差异
        entities1 = set(graph1.entities.keys())
        entities2 = set(graph2.entities.keys())

        added_entities = entities2 - entities1
        removed_entities = entities1 - entities2

        return {
            'status': 'success',
            'branch1': branch1,
            'branch2': branch2,
            'file_changes': {
                'added': list(added_files),
                'removed': list(removed_files),
                'modified': len(common_files),  # 简化版，实际可以比较hash
                'total_files': {'branch1': len(files1), 'branch2': len(files2)}
            },
            'entity_changes': {
                'added': list(added_entities),
                'removed': list(removed_entities),
                'total_entities': {'branch1': len(entities1), 'branch2': len(entities2)}
            },
            'complexity_changes': {
                'branch1': graph1.context.complexity_distribution if graph1.context else {},
                'branch2': graph2.context.complexity_distribution if graph2.context else {}
            }
        }

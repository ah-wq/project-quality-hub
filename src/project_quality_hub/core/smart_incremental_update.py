"""智能增量更新系统，提供文件变更监控与知识图谱增量刷新能力。"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from .project_mind import FileNode, ProjectKnowledgeGraph
from .project_memory import ProjectMemoryManager

logger = logging.getLogger(__name__)

@dataclass
class FileChangeInfo:
    """文件变更信息"""
    file_path: str
    change_type: str  # 'created', 'modified', 'deleted', 'moved'
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    timestamp: datetime = None
    content_changed: bool = False
    metadata_changed: bool = False

class SmartFileHandler(FileSystemEventHandler):
    """智能文件监控处理器"""

    def __init__(self, update_manager):
        self.update_manager = update_manager
        self.batch_changes: Dict[str, FileChangeInfo] = {}
        self.batch_timer = None
        self.batch_delay = 2.0  # 2秒批处理延迟

    def on_modified(self, event):
        if not event.is_directory:
            self._queue_change(event.src_path, 'modified')

    def on_created(self, event):
        if not event.is_directory:
            self._queue_change(event.src_path, 'created')

    def on_deleted(self, event):
        if not event.is_directory:
            self._queue_change(event.src_path, 'deleted')

    def on_moved(self, event):
        if not event.is_directory:
            # 处理文件移动/重命名
            self._queue_change(event.src_path, 'deleted')
            self._queue_change(event.dest_path, 'created')

    def _queue_change(self, file_path: str, change_type: str):
        """将文件变更加入队列"""
        if not self.update_manager._should_monitor_file(file_path):
            return

        file_path = str(Path(file_path).resolve())

        # 计算文件hash
        new_hash = None
        if change_type != 'deleted' and Path(file_path).exists():
            try:
                new_hash = self.update_manager._calculate_file_hash(file_path)
            except Exception:
                pass

        change_info = FileChangeInfo(
            file_path=file_path,
            change_type=change_type,
            new_hash=new_hash,
            timestamp=datetime.now()
        )

        self.batch_changes[file_path] = change_info

        # 重置批处理定时器
        if self.batch_timer:
            self.batch_timer.cancel()

        self.batch_timer = threading.Timer(self.batch_delay, self._process_batch_changes)
        self.batch_timer.start()

    def _process_batch_changes(self):
        """批处理文件变更"""
        if self.batch_changes:
            changes = dict(self.batch_changes)
            self.batch_changes.clear()

            # 异步处理变更
            threading.Thread(
                target=self.update_manager._process_file_changes,
                args=(changes,),
                daemon=True
            ).start()

class SmartIncrementalUpdater:
    """智能增量更新管理器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).absolute()
        self.memory_manager = ProjectMemoryManager()
        self.observer = None
        self.monitoring = False
        self._observer_class = None

        # 忽略的文件模式
        self.ignore_patterns = {
            '.git', '.DS_Store', '__pycache__', 'node_modules',
            '.next', '.nuxt', 'dist', 'build', '.vscode',
            '*.log', '*.tmp', '*.temp', '*.cache'
        }

        # 支持的代码文件扩展名
        self.code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.vue', '.java',
            '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs',
            '.php', '.rb', '.swift', '.kt', '.scala', '.md',
            '.json', '.yaml', '.yml', '.xml', '.css', '.scss',
            '.less', '.html', '.htm'
        }

    def _should_force_polling(self) -> bool:
        """检查是否强制使用轮询监控"""
        flag = os.environ.get("WATCHDOG_FORCE_POLLING", "")
        if not flag:
            return False
        return flag.lower() not in {"0", "false", "no"}

    def _candidate_observers(self):
        """生成可用的监控实现列表"""
        if self._should_force_polling():
            return [PollingObserver]
        return [Observer, PollingObserver]

    def _should_monitor_file(self, file_path: str) -> bool:
        """判断是否应该监控此文件"""
        path = Path(file_path)

        # 检查是否在忽略列表中
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if path.name.endswith(pattern[1:]):
                    return False
            else:
                if pattern in path.parts:
                    return False

        # 检查文件扩展名
        return path.suffix.lower() in self.code_extensions

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件内容hash"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""

    def _get_git_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取Git文件信息"""
        try:
            # 获取文件最后修改的commit信息
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%ct|%an", "--", file_path],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            if result.stdout.strip():
                hash_str, timestamp, author = result.stdout.strip().split("|")
                return {
                    'last_commit_hash': hash_str,
                    'last_commit_time': datetime.fromtimestamp(int(timestamp)),
                    'last_author': author
                }
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            pass

        return {}

    def _analyze_content_changes(self, file_path: str, old_hash: str, new_hash: str) -> Dict[str, Any]:
        """分析文件内容具体变更"""
        if old_hash == new_hash:
            return {'content_changed': False}

        changes = {
            'content_changed': True,
            'hash_changed': True,
            'lines_changed': 0,
            'entities_affected': [],
            'risk_level': 'low'
        }

        try:
            # 使用git diff分析变更
            result = subprocess.run(
                ["git", "diff", "--numstat", "HEAD~1", "HEAD", "--", file_path],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.stdout.strip():
                lines = result.stdout.strip().split('\t')
                if len(lines) >= 2:
                    added = int(lines[0]) if lines[0] != '-' else 0
                    deleted = int(lines[1]) if lines[1] != '-' else 0
                    changes['lines_changed'] = added + deleted

                    # 评估风险级别
                    if changes['lines_changed'] > 100:
                        changes['risk_level'] = 'high'
                    elif changes['lines_changed'] > 20:
                        changes['risk_level'] = 'medium'

        except (subprocess.CalledProcessError, ValueError):
            pass

        return changes

    def _process_file_changes(self, changes: Dict[str, FileChangeInfo]):
        """处理批量文件变更"""
        logger.info(f"🔄 处理 {len(changes)} 个文件变更")

        # 加载当前项目图谱
        knowledge_graph = self.memory_manager.load_project(str(self.project_root))
        if not knowledge_graph:
            logger.warning("无法加载项目图谱，执行完整重新分析")
            self.full_reanalysis()
            return

        # 分析每个变更的文件
        updated_files = set()
        affected_entities = set()

        for file_path, change_info in changes.items():
            try:
                self._process_single_file_change(knowledge_graph, change_info)
                updated_files.add(file_path)

                # 分析影响的实体
                if file_path in knowledge_graph.files:
                    file_entities = knowledge_graph.files[file_path].entities
                    affected_entities.update(entity.name for entity in file_entities)

            except Exception as e:
                logger.error(f"处理文件变更失败 {file_path}: {e}")

        # 更新依赖关系
        if updated_files:
            self._update_dependencies(knowledge_graph, updated_files)

        # 保存更新后的图谱
        if self.memory_manager.save_project(knowledge_graph):
            logger.info(f"✅ 增量更新完成: {len(updated_files)} 个文件, {len(affected_entities)} 个实体")
        else:
            logger.error("❌ 增量更新保存失败")

    def _process_single_file_change(self, knowledge_graph: ProjectKnowledgeGraph, change_info: FileChangeInfo):
        """处理单个文件的变更"""
        file_path = change_info.file_path

        if change_info.change_type == 'deleted':
            # 删除文件
            if file_path in knowledge_graph.files:
                del knowledge_graph.files[file_path]

            # 删除相关实体
            entities_to_remove = [
                name for name, entity in knowledge_graph.entities.items()
                if entity.file_path == file_path
            ]
            for entity_name in entities_to_remove:
                del knowledge_graph.entities[entity_name]

        elif change_info.change_type in ['created', 'modified']:
            # 重新分析文件
            if Path(file_path).exists():
                # 获取Git信息
                git_info = self._get_git_file_info(file_path)

                # 分析文件内容变更
                old_hash = knowledge_graph.files.get(file_path, FileNode("", "", 0, 0, datetime.now(), "")).file_hash
                change_summary = self._analyze_content_changes(
                    file_path, old_hash, change_info.new_hash or ""
                )

                # 重新分析文件（简化版）
                relative_path = str(Path(file_path).relative_to(self.project_root))
                knowledge_graph._analyze_single_file(file_path, relative_path)

                # 更新Git信息
                if file_path in knowledge_graph.files and git_info:
                    file_node = knowledge_graph.files[file_path]
                    if 'last_commit_time' in git_info:
                        file_node.last_modified = git_info['last_commit_time']
                if change_summary.get("risk_level") in {"medium", "high"}:
                    logger.warning(
                        "文件 %s 检测到 %s 风险级别的内容变更 (行变动: %s)",
                        file_path,
                        change_summary["risk_level"],
                        change_summary.get("lines_changed", 0),
                    )

    def _update_dependencies(self, knowledge_graph: ProjectKnowledgeGraph, updated_files: Set[str]):
        """更新受影响文件的依赖关系"""
        # 重新计算依赖关系（简化版）
        for file_path in updated_files:
            if file_path in knowledge_graph.files:
                file_node = knowledge_graph.files[file_path]
                # 重新分析导入和导出
                knowledge_graph._analyze_imports_exports(file_path, file_node)

    def start_monitoring(self):
        """开始实时监控"""
        if self.monitoring:
            logger.warning("监控已在运行")
            return

        logger.info("🔍 开始监控项目: %s", self.project_root)

        event_handler = SmartFileHandler(self)
        observer = None
        last_error: Exception | None = None

        for observer_cls in self._candidate_observers():
            candidate = None
            try:
                candidate = observer_cls()
                candidate.schedule(event_handler, str(self.project_root), recursive=True)
                candidate.start()
            except Exception as exc:
                last_error = exc
                logger.warning("无法使用%s启动文件监控: %s", observer_cls.__name__, exc)
                if candidate is not None:
                    try:
                        candidate.stop()
                    except Exception:
                        pass
            else:
                observer = candidate
                self._observer_class = observer_cls
                break

        if observer is None:
            message = "默认监控与轮询监控均无法启动" if isinstance(last_error, Exception) else "无法启动文件监控"
            raise RuntimeError(f"{message}: {last_error}") from last_error

        self.observer = observer
        self.monitoring = True
        logger.info("✅ 实时监控已启动（模式: %s）", self._observer_class.__name__)

    def stop_monitoring(self):
        """停止实时监控"""
        if not self.monitoring or not self.observer:
            return

        logger.info("🛑 停止项目监控")

        self.observer.stop()
        self.observer.join()
        self.monitoring = False

        logger.info("✅ 监控已停止")

    def full_reanalysis(self):
        """执行完整重新分析"""
        logger.info("🔄 执行完整项目重新分析")

        knowledge_graph = ProjectKnowledgeGraph(str(self.project_root))
        knowledge_graph.analyze_project()

        if self.memory_manager.save_project(knowledge_graph):
            logger.info("✅ 完整重新分析完成")
            return True
        else:
            logger.error("❌ 完整重新分析失败")
            return False

    def force_update(self) -> Dict[str, Any]:
        """强制更新项目图谱"""
        logger.info("🔧 强制更新项目图谱")

        # 停止监控
        was_monitoring = self.monitoring
        if was_monitoring:
            self.stop_monitoring()

        # 执行完整分析
        success = self.full_reanalysis()

        # 重启监控
        if was_monitoring:
            self.start_monitoring()

        return {
            'status': 'success' if success else 'failed',
            'timestamp': datetime.now(),
            'monitoring_restarted': was_monitoring
        }

    def get_update_status(self) -> Dict[str, Any]:
        """获取更新状态"""
        knowledge_graph = self.memory_manager.load_project(str(self.project_root))

        return {
            'monitoring': self.monitoring,
            'project_root': str(self.project_root),
            'last_analysis': knowledge_graph.context.last_analysis if knowledge_graph and knowledge_graph.context else None,
            'files_count': len(knowledge_graph.files) if knowledge_graph else 0,
            'entities_count': len(knowledge_graph.entities) if knowledge_graph else 0,
            'supported_extensions': list(self.code_extensions),
            'ignore_patterns': list(self.ignore_patterns)
        }

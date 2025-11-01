"""增强版项目图谱接口，集成多分支支持和智能增量更新。"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .project_mind_interface import ProjectMindInterface
from .multi_branch import MultiBranchProjectMind
from .smart_incremental_update import SmartIncrementalUpdater

logger = logging.getLogger(__name__)

class EnhancedProjectMindInterface:
    """增强版项目图谱接口 - 支持多分支和智能更新"""

    def __init__(self):
        self.original_interface = ProjectMindInterface()
        self.branch_managers: Dict[str, MultiBranchProjectMind] = {}
        self.updaters: Dict[str, SmartIncrementalUpdater] = {}

    def _get_branch_manager(self, project_root: str) -> MultiBranchProjectMind:
        """获取或创建分支管理器"""
        if project_root not in self.branch_managers:
            self.branch_managers[project_root] = MultiBranchProjectMind(project_root)
        return self.branch_managers[project_root]

    def _get_updater(self, project_root: str) -> SmartIncrementalUpdater:
        """获取或创建增量更新器"""
        if project_root not in self.updaters:
            self.updaters[project_root] = SmartIncrementalUpdater(project_root)
        return self.updaters[project_root]

    # =========================
    # 原有功能的封装
    # =========================

    def analyze_project(self, project_root: str, *, force: bool = False, enable_monitoring: bool = False) -> Dict[str, Any]:
        """分析项目（支持分支感知）

        Args:
            project_root: 项目根目录
            force: 是否强制重新分析当前分支
            enable_monitoring: 成功分析后是否自动启动智能监控
        """
        try:
            project_root = str(Path(project_root).absolute())

            # 使用分支感知的分析
            branch_manager = self._get_branch_manager(project_root)
            result = branch_manager.analyze_branch_project(force_update=force)

            updater = self._get_updater(project_root)
            monitoring_active = updater.monitoring

            if enable_monitoring and not monitoring_active:
                try:
                    updater.start_monitoring()
                    monitoring_active = True
                    result['monitoring_started'] = True
                except Exception as e:
                    logger.warning("启动监控失败: %s", e)
                    result['monitoring_started'] = False

            result['monitoring_active'] = monitoring_active
            result.setdefault('monitoring_started', monitoring_active)
            result['monitoring_enabled'] = enable_monitoring or monitoring_active

            return result

        except Exception as e:
            return {'error': f'分析项目失败: {str(e)}'}

    def search_entities(self, project_root: str, query: str, limit: int = 10) -> Dict[str, Any]:
        """搜索代码实体"""
        return self.original_interface.search_entities(project_root, query, limit)

    def get_file_dependencies(self, project_root: str, file_path: str) -> Dict[str, Any]:
        """获取文件依赖关系"""
        return self.original_interface.get_file_dependencies(project_root, file_path)

    def get_project_summary(self, project_root: str) -> Dict[str, Any]:
        """获取项目摘要（增强版）"""
        try:
            project_root = str(Path(project_root).absolute())

            # 获取原始摘要
            base_summary = self.original_interface.get_project_summary(project_root)

            # 添加分支信息
            branch_manager = self._get_branch_manager(project_root)
            branch_info = branch_manager.list_branch_projects()

            # 添加更新状态
            updater = self._get_updater(project_root)
            update_status = updater.get_update_status()

            # 合并信息
            enhanced_summary = {
                **base_summary,
                'branch_info': branch_info,
                'update_status': update_status,
                'enhanced_features': {
                    'multi_branch_support': True,
                    'real_time_monitoring': update_status.get('monitoring', False),
                    'incremental_updates': True
                }
            }

            return enhanced_summary

        except Exception as e:
            return {'error': f'获取项目摘要失败: {str(e)}'}

    # =========================
    # 多分支功能
    # =========================

    def list_branches(self, project_root: str) -> Dict[str, Any]:
        """列出所有分支及其分析状态"""
        try:
            project_root = str(Path(project_root).absolute())
            branch_manager = self._get_branch_manager(project_root)
            return branch_manager.list_branch_projects()
        except Exception as e:
            return {'error': f'列出分支失败: {str(e)}'}

    def analyze_branch(self, project_root: str, branch_name: str, force: bool = False) -> Dict[str, Any]:
        """分析特定分支"""
        try:
            project_root = str(Path(project_root).absolute())
            branch_manager = self._get_branch_manager(project_root)
            return branch_manager.analyze_branch_project(branch_name, force_update=force)
        except Exception as e:
            return {'error': f'分析分支失败: {str(e)}'}

    def switch_branch(self, project_root: str, branch_name: str) -> Dict[str, Any]:
        """切换到指定分支并分析"""
        try:
            project_root = str(Path(project_root).absolute())

            # 停止当前监控
            updater = self._get_updater(project_root)
            was_monitoring = updater.monitoring
            if was_monitoring:
                updater.stop_monitoring()

            # 切换分支
            branch_manager = self._get_branch_manager(project_root)
            result = branch_manager.switch_to_branch_analysis(branch_name)

            # 重启监控
            if was_monitoring and result.get('status') == 'analyzed':
                try:
                    updater.start_monitoring()
                    result['monitoring_restarted'] = True
                except Exception as e:
                    logger.warning(f"重启监控失败: {e}")
                    result['monitoring_restarted'] = False

            return result

        except Exception as e:
            return {'error': f'切换分支失败: {str(e)}'}

    def compare_branches(self, project_root: str, branch1: str, branch2: str) -> Dict[str, Any]:
        """比较两个分支的差异"""
        try:
            project_root = str(Path(project_root).absolute())
            branch_manager = self._get_branch_manager(project_root)
            return branch_manager.compare_branches(branch1, branch2)
        except Exception as e:
            return {'error': f'比较分支失败: {str(e)}'}

    # =========================
    # 智能更新功能
    # =========================

    def start_monitoring(self, project_root: str) -> Dict[str, Any]:
        """开始实时监控"""
        try:
            project_root = str(Path(project_root).absolute())
            updater = self._get_updater(project_root)

            if updater.monitoring:
                return {'status': 'already_running', 'message': '监控已在运行'}

            updater.start_monitoring()
            return {'status': 'started', 'message': '实时监控已启动'}

        except Exception as e:
            return {'error': f'启动监控失败: {str(e)}'}

    def stop_monitoring(self, project_root: str) -> Dict[str, Any]:
        """停止实时监控"""
        try:
            project_root = str(Path(project_root).absolute())
            updater = self._get_updater(project_root)

            if not updater.monitoring:
                return {'status': 'not_running', 'message': '监控未在运行'}

            updater.stop_monitoring()
            return {'status': 'stopped', 'message': '监控已停止'}

        except Exception as e:
            return {'error': f'停止监控失败: {str(e)}'}

    def force_update(self, project_root: str) -> Dict[str, Any]:
        """强制更新项目图谱"""
        try:
            project_root = str(Path(project_root).absolute())
            updater = self._get_updater(project_root)
            return updater.force_update()
        except Exception as e:
            return {'error': f'强制更新失败: {str(e)}'}

    def get_update_status(self, project_root: str) -> Dict[str, Any]:
        """获取更新状态"""
        try:
            project_root = str(Path(project_root).absolute())
            updater = self._get_updater(project_root)
            return updater.get_update_status()
        except Exception as e:
            return {'error': f'获取状态失败: {str(e)}'}

    # =========================
    # 新增高级功能
    # =========================

    def smart_analysis(self, project_root: str, branch_name: str = None) -> Dict[str, Any]:
        """智能分析 - 自动检测最优策略"""
        try:
            project_root = str(Path(project_root).absolute())

            # 获取当前状态
            branch_manager = self._get_branch_manager(project_root)
            current_branch = branch_name or branch_manager.current_branch

            # 检查是否需要更新
            existing_analysis = branch_manager._load_branch_project(current_branch)
            branch_context = branch_manager.update_branch_context(current_branch)

            needs_update = True
            if existing_analysis:
                needs_update = not branch_manager._is_project_up_to_date(existing_analysis, branch_context)

            analysis_result = {
                'branch': current_branch,
                'needs_update': needs_update,
                'strategy': 'incremental' if existing_analysis else 'full'
            }

            if needs_update:
                # 执行分析
                if existing_analysis:
                    # 增量更新
                    updater = self._get_updater(project_root)
                    update_result = updater.force_update()
                    analysis_result.update(update_result)
                else:
                    # 完整分析
                    branch_result = branch_manager.analyze_branch_project(current_branch, force_update=True)
                    analysis_result.update(branch_result)

                # 启动监控
                updater = self._get_updater(project_root)
                if not updater.monitoring:
                    try:
                        updater.start_monitoring()
                        analysis_result['monitoring_started'] = True
                    except Exception as e:
                        logger.warning(f"启动监控失败: {e}")
                        analysis_result['monitoring_started'] = False
            else:
                analysis_result['status'] = 'up_to_date'
                analysis_result['message'] = '项目图谱已是最新'

            return analysis_result

        except Exception as e:
            return {'error': f'智能分析失败: {str(e)}'}

    def health_check(self, project_root: str) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            project_root = str(Path(project_root).absolute())

            health_status = {
                'overall': 'healthy',
                'timestamp': datetime.now(),
                'checks': {}
            }

            # 检查项目存在性
            if not Path(project_root).exists():
                health_status['overall'] = 'error'
                health_status['checks']['project_exists'] = {'status': 'failed', 'message': '项目路径不存在'}
                return health_status

            health_status['checks']['project_exists'] = {'status': 'passed'}

            # 检查Git仓库
            try:
                branch_manager = self._get_branch_manager(project_root)
                current_branch = branch_manager.current_branch
                health_status['checks']['git_repository'] = {
                    'status': 'passed',
                    'current_branch': current_branch
                }
            except Exception:
                health_status['checks']['git_repository'] = {
                    'status': 'warning',
                    'message': '不是Git仓库或Git不可用'
                }

            # 检查项目图谱
            try:
                summary = self.get_project_summary(project_root)
                if 'error' not in summary:
                    health_status['checks']['project_graph'] = {
                        'status': 'passed',
                        'files_count': summary.get('files_count', 0),
                        'entities_count': summary.get('entities_count', 0)
                    }
                else:
                    health_status['checks']['project_graph'] = {
                        'status': 'failed',
                        'message': '项目图谱加载失败'
                    }
            except Exception as e:
                health_status['checks']['project_graph'] = {
                    'status': 'failed',
                    'message': f'项目图谱检查失败: {str(e)}'
                }

            # 检查监控状态
            try:
                updater = self._get_updater(project_root)
                status = updater.get_update_status()
                health_status['checks']['monitoring'] = {
                    'status': 'passed' if status.get('monitoring') else 'warning',
                    'monitoring_active': status.get('monitoring', False)
                }
            except Exception as e:
                health_status['checks']['monitoring'] = {
                    'status': 'error',
                    'message': f'监控状态检查失败: {str(e)}'
                }

            # 评估整体健康状态
            failed_checks = [check for check in health_status['checks'].values() if check['status'] == 'failed']
            warning_checks = [check for check in health_status['checks'].values() if check['status'] == 'warning']

            if failed_checks:
                health_status['overall'] = 'error'
            elif warning_checks:
                health_status['overall'] = 'warning'

            return health_status

        except Exception as e:
            return {
                'overall': 'error',
                'timestamp': datetime.now(),
                'error': f'健康检查失败: {str(e)}'
            }

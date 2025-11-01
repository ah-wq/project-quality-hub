"""ProjectMind 接口，为外部调用提供项目分析和记忆功能。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

from .project_mind import ProjectKnowledgeGraph
from .project_memory import get_memory_manager

logger = logging.getLogger(__name__)


class ProjectMindInterface:
    """ProjectMind的Claude集成接口"""
    
    def __init__(self):
        self.memory_manager = get_memory_manager()
    
    def analyze_project(self, project_root: str, force_reanalysis: bool = False) -> Dict[str, Any]:
        """分析项目并返回结果"""
        project_root = str(Path(project_root).absolute())
        
        if not Path(project_root).exists():
            return {'error': f'项目路径不存在: {project_root}'}
        
        try:
            # 尝试从内存加载
            if not force_reanalysis:
                knowledge_graph = self.memory_manager.load_project(project_root)
                if knowledge_graph:
                    logger.info("Loaded project from memory: %s", knowledge_graph.context.project_name)
                    return knowledge_graph.export_project_summary()
            
            # 执行新的分析
            logger.info("Starting analysis for project: %s", Path(project_root).name)
            knowledge_graph = ProjectKnowledgeGraph(project_root)
            knowledge_graph.analyze_project()
            
            # 保存到记忆中
            if self.memory_manager.save_project(knowledge_graph):
                logger.info("Project analysis saved to memory store")
            
            return knowledge_graph.export_project_summary()
        
        except Exception as e:
            return {'error': f'分析项目失败: {str(e)}'}
    
    def predict_change_impact(self, project_root: str, file_path: str) -> Dict[str, Any]:
        """预测代码变更影响"""
        try:
            knowledge_graph = self.memory_manager.load_project(project_root)
            if not knowledge_graph:
                return {'error': '项目未分析，请先运行项目分析'}
            
            # 确保文件路径是绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(project_root, file_path)
            
            return knowledge_graph.predict_change_impact(file_path)
        
        except Exception as e:
            return {'error': f'影响分析失败: {str(e)}'}
    
    def get_file_context(self, project_root: str, file_path: str) -> Dict[str, Any]:
        """获取文件上下文信息"""
        try:
            knowledge_graph = self.memory_manager.load_project(project_root)
            if not knowledge_graph:
                return {'error': '项目未分析，请先运行项目分析'}
            
            if not os.path.isabs(file_path):
                file_path = os.path.join(project_root, file_path)
            
            if file_path not in knowledge_graph.files:
                return {'error': f'文件未找到: {file_path}'}
            
            file_node = knowledge_graph.files[file_path]
            dependencies = knowledge_graph.get_file_dependencies(file_path)
            dependents = knowledge_graph.get_file_dependents(file_path)
            
            return {
                'file_info': {
                    'path': file_path,
                    'language': file_node.language,
                    'size_bytes': file_node.size_bytes,
                    'line_count': file_node.line_count,
                    'risk_score': file_node.risk_score,
                    'last_modified': file_node.last_modified.isoformat()
                },
                'entities': [
                    {
                        'name': entity.name,
                        'type': entity.entity_type,
                        'line': entity.line_number,
                        'signature': entity.signature,
                        'docstring': entity.docstring
                    }
                    for entity in file_node.entities
                ],
                'dependencies': dependencies,
                'dependents': dependents,
                'imports': file_node.imports,
                'exports': file_node.exports
            }
        
        except Exception as e:
            return {'error': f'获取文件上下文失败: {str(e)}'}
    
    def search_entities(self, project_root: str, entity_name: str) -> Dict[str, Any]:
        """搜索代码实体"""
        try:
            knowledge_graph = self.memory_manager.load_project(project_root)
            if not knowledge_graph:
                return {'error': '项目未分析，请先运行项目分析'}
            
            entities = knowledge_graph.get_entity_by_name(entity_name)
            
            return {
                'query': entity_name,
                'total_found': len(entities),
                'entities': [
                    {
                        'name': entity.name,
                        'type': entity.entity_type,
                        'file': entity.file_path,
                        'line': entity.line_number,
                        'signature': entity.signature,
                        'complexity_score': entity.complexity_score,
                        'usage_count': entity.usage_count
                    }
                    for entity in entities
                ]
            }
        
        except Exception as e:
            return {'error': f'搜索实体失败: {str(e)}'}
    
    def get_project_summary(self, project_root: str) -> Dict[str, Any]:
        """获取项目摘要"""
        try:
            project_root = str(Path(project_root).absolute())
            knowledge_graph = self.memory_manager.load_project(project_root)
            if not knowledge_graph:
                return {'error': '项目未分析，请先运行项目分析'}
            return knowledge_graph.export_project_summary()
        except Exception as e:
            return {'error': f'获取项目摘要失败: {str(e)}'}

    def update_project(self, project_root: str) -> Dict[str, Any]:
        """增量更新项目"""
        try:
            project_root = str(Path(project_root).absolute())
            success = self.memory_manager.update_project_incremental(project_root)
            
            if success:
                # 重新获取更新后的项目摘要
                knowledge_graph = self.memory_manager.load_project(project_root)
                if knowledge_graph:
                    return {
                        'success': True,
                        'message': '项目更新完成',
                        'summary': knowledge_graph.export_project_summary()
                    }
            
            return {'error': '项目更新失败'}
        
        except Exception as e:
            return {'error': f'更新项目失败: {str(e)}'}
    
    def get_project_list(self) -> Dict[str, Any]:
        """获取所有已分析的项目列表"""
        try:
            projects = self.memory_manager.get_project_list()
            return {
                'total_projects': len(projects),
                'projects': projects
            }
        
        except Exception as e:
            return {'error': f'获取项目列表失败: {str(e)}'}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return self.memory_manager.get_storage_stats()

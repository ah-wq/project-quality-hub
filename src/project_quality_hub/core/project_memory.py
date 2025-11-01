"""项目记忆持久化系统。"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .project_mind import CodeEntity, FileNode, ProjectContext, ProjectKnowledgeGraph

logger = logging.getLogger(__name__)


class ProjectMemoryManager:
    """项目记忆管理器 - 持久化存储和快速恢复"""
    
    def __init__(self, storage_dir: str = None):
        self.storage_dir = self._resolve_storage_dir(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件
        self.db_path = self.storage_dir / "project_memory.db"
        
        # 缓存目录
        self.cache_dir = self.storage_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # 内存缓存
        self._cache: Dict[str, ProjectKnowledgeGraph] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # 缓存配置
        self.max_cache_size = 5  # 最多缓存5个项目
        self.cache_ttl = timedelta(hours=2)  # 缓存2小时有效
    def _resolve_storage_dir(self, storage_dir: str | None) -> Path:
        """Determine storage directory, migrating legacy data when needed."""
        if storage_dir:
            return Path(storage_dir)

        default_dir = Path.home() / ".project-quality-hub"
        legacy_dir = Path.home() / ".mcp-enhanced-quality"

        if legacy_dir.exists() and not default_dir.exists():
            try:
                shutil.move(str(legacy_dir), str(default_dir))
                logger.info("Migrated legacy storage from %s to %s", legacy_dir, default_dir)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to migrate legacy storage: %s", exc)
                return legacy_dir

        return default_dir
    
    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                -- 项目基础信息表
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    project_root TEXT UNIQUE NOT NULL,
                    project_name TEXT NOT NULL,
                    framework_type TEXT,
                    main_language TEXT,
                    architecture_pattern TEXT,
                    build_system TEXT,
                    package_manager TEXT,
                    version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analysis_version INTEGER DEFAULT 1,
                    total_files INTEGER DEFAULT 0,
                    total_lines INTEGER DEFAULT 0,
                    complexity_distribution TEXT, -- JSON
                    is_active BOOLEAN DEFAULT 1
                );
                
                -- 文件信息表
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    relative_path TEXT,
                    language TEXT,
                    size_bytes INTEGER,
                    line_count INTEGER,
                    file_hash TEXT,
                    risk_score REAL,
                    change_frequency INTEGER DEFAULT 0,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    UNIQUE(project_id, file_path)
                );
                
                -- 代码实体表
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    entity_type TEXT, -- function, class, variable, etc.
                    signature TEXT,
                    docstring TEXT,
                    line_number INTEGER,
                    complexity_score REAL DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (file_id) REFERENCES files (id)
                );
                
                -- 依赖关系表
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    from_file_id INTEGER,
                    to_file_id INTEGER,
                    from_entity_id INTEGER,
                    to_entity_id INTEGER,
                    relation_type TEXT, -- imports, calls, extends, etc.
                    strength REAL DEFAULT 1.0,
                    line_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (from_file_id) REFERENCES files (id),
                    FOREIGN KEY (to_file_id) REFERENCES files (id),
                    FOREIGN KEY (from_entity_id) REFERENCES entities (id),
                    FOREIGN KEY (to_entity_id) REFERENCES entities (id)
                );
                
                -- 变更历史表
                CREATE TABLE IF NOT EXISTS change_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    file_path TEXT,
                    change_type TEXT, -- created, modified, deleted, renamed
                    old_hash TEXT,
                    new_hash TEXT,
                    change_summary TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                );
                
                -- 项目配置表
                CREATE TABLE IF NOT EXISTS project_configs (
                    project_id TEXT PRIMARY KEY,
                    ignore_patterns TEXT, -- JSON array
                    custom_rules TEXT,    -- JSON object
                    analysis_options TEXT, -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                );
                
                -- 创建索引优化查询性能
                CREATE INDEX IF NOT EXISTS idx_projects_root ON projects(project_root);
                CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at);
                CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id);
                CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);
                CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id);
                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
                CREATE INDEX IF NOT EXISTS idx_dependencies_project ON dependencies(project_id);
                CREATE INDEX IF NOT EXISTS idx_change_history_project ON change_history(project_id);
            ''')
            logger.info("数据库初始化完成")
    
    def get_project_id(self, project_root: str) -> str:
        """根据项目路径生成项目ID"""
        return hashlib.md5(str(Path(project_root).absolute()).encode()).hexdigest()
    
    def save_project(self, knowledge_graph: ProjectKnowledgeGraph) -> bool:
        """保存项目知识图谱到持久化存储"""
        try:
            project_id = self.get_project_id(knowledge_graph.project_root)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('BEGIN TRANSACTION')
                
                try:
                    # 保存项目基础信息
                    self._save_project_context(conn, project_id, knowledge_graph.context)
                    
                    # 保存文件信息
                    self._save_files(conn, project_id, knowledge_graph.files)
                    
                    # 保存代码实体
                    self._save_entities(conn, project_id, knowledge_graph.entities)
                    
                    # 保存依赖关系
                    self._save_dependencies(conn, project_id, knowledge_graph.graph)
                    
                    # 保存完整的知识图谱到缓存文件
                    cache_file = self.cache_dir / f"{project_id}.pkl"
                    with open(cache_file, 'wb') as f:
                        pickle.dump(knowledge_graph, f)
                    
                    conn.execute('COMMIT')
                    
                    # 更新内存缓存
                    self._cache[project_id] = knowledge_graph
                    self._cache_timestamps[project_id] = datetime.now()
                    
                    logger.info(f"项目保存成功: {knowledge_graph.context.project_name}")
                    return True
                    
                except Exception as e:
                    conn.execute('ROLLBACK')
                    logger.error(f"保存项目失败: {e}")
                    return False
        
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def _save_project_context(self, conn: sqlite3.Connection, project_id: str, context: ProjectContext):
        """保存项目上下文信息"""
        complexity_json = json.dumps(context.complexity_distribution)
        
        conn.execute('''
            INSERT OR REPLACE INTO projects 
            (id, project_root, project_name, framework_type, main_language, 
             architecture_pattern, build_system, package_manager, version,
             total_files, total_lines, complexity_distribution, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            project_id, context.project_root, context.project_name,
            context.framework_type, context.main_language, 
            context.architecture_pattern, context.build_system,
            context.package_manager, context.version,
            context.total_files, context.total_lines, complexity_json
        ))
    
    def _save_files(self, conn: sqlite3.Connection, project_id: str, files: Dict[str, FileNode]):
        """保存文件信息"""
        # 清除旧的文件记录
        conn.execute('DELETE FROM files WHERE project_id = ?', (project_id,))
        
        for file_path, file_node in files.items():
            relative_path = str(Path(file_path).relative_to(Path(file_node.file_path).parent.parent))
            
            conn.execute('''
                INSERT INTO files 
                (project_id, file_path, relative_path, language, size_bytes, 
                 line_count, file_hash, risk_score, change_frequency, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id, file_path, relative_path, file_node.language,
                file_node.size_bytes, file_node.line_count, file_node.file_hash,
                file_node.risk_score, file_node.change_frequency, file_node.last_modified
            ))
    
    def _save_entities(self, conn: sqlite3.Connection, project_id: str, entities: Dict[str, CodeEntity]):
        """保存代码实体"""
        # 清除旧的实体记录
        conn.execute('DELETE FROM entities WHERE project_id = ?', (project_id,))
        
        # 获取文件ID映射
        file_id_map = {}
        cursor = conn.execute('SELECT file_path, id FROM files WHERE project_id = ?', (project_id,))
        for file_path, file_id in cursor.fetchall():
            file_id_map[file_path] = file_id
        
        for entity_key, entity in entities.items():
            file_id = file_id_map.get(entity.file_path)
            if file_id:
                conn.execute('''
                    INSERT INTO entities 
                    (project_id, file_id, name, entity_type, signature, docstring,
                     line_number, complexity_score, usage_count, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id, file_id, entity.name, entity.entity_type,
                    entity.signature, entity.docstring, entity.line_number,
                    entity.complexity_score, entity.usage_count, entity.last_modified
                ))
    
    def _save_dependencies(self, conn: sqlite3.Connection, project_id: str, graph):
        """保存依赖关系"""
        # 清除旧的依赖记录
        conn.execute('DELETE FROM dependencies WHERE project_id = ?', (project_id,))
        
        # 获取文件ID映射
        file_id_map = {}
        cursor = conn.execute('SELECT file_path, id FROM files WHERE project_id = ?', (project_id,))
        for file_path, file_id in cursor.fetchall():
            file_id_map[file_path] = file_id
        
        # 保存图中的边（依赖关系）
        for from_node, to_node, edge_data in graph.edges(data=True):
            from_file_id = file_id_map.get(from_node)
            to_file_id = file_id_map.get(to_node)
            
            if from_file_id and to_file_id:
                conn.execute('''
                    INSERT INTO dependencies 
                    (project_id, from_file_id, to_file_id, relation_type, strength)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    project_id, from_file_id, to_file_id,
                    edge_data.get('relation_type', 'unknown'),
                    edge_data.get('strength', 1.0)
                ))
    
    def load_project(self, project_root: str, use_cache: bool = True) -> Optional[ProjectKnowledgeGraph]:
        """加载项目知识图谱"""
        project_id = self.get_project_id(project_root)
        
        # 检查内存缓存
        if use_cache and project_id in self._cache:
            cache_time = self._cache_timestamps.get(project_id)
            if cache_time and (datetime.now() - cache_time) < self.cache_ttl:
                logger.info(f"从内存缓存加载项目: {project_id}")
                return self._cache[project_id]
        
        # 检查文件缓存
        cache_file = self.cache_dir / f"{project_id}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    knowledge_graph = pickle.load(f)
                    
                # 验证缓存是否过期
                if self._is_cache_valid(knowledge_graph):
                    logger.info(f"从文件缓存加载项目: {project_id}")
                    
                    # 更新内存缓存
                    self._cache[project_id] = knowledge_graph
                    self._cache_timestamps[project_id] = datetime.now()
                    
                    return knowledge_graph
            except Exception as e:
                logger.warning(f"缓存文件损坏: {e}")
        
        # 从数据库重建
        return self._load_from_database(project_id, project_root)
    
    def _is_cache_valid(self, knowledge_graph: ProjectKnowledgeGraph) -> bool:
        """检查缓存是否有效"""
        # 检查关键文件是否被修改
        for file_path, file_node in knowledge_graph.files.items():
            if Path(file_path).exists():
                current_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                if current_mtime > file_node.last_modified:
                    return False
        
        return True
    
    def _load_from_database(self, project_id: str, project_root: str) -> Optional[ProjectKnowledgeGraph]:
        """从数据库重建知识图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 检查项目是否存在
                cursor = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
                project_row = cursor.fetchone()
                
                if not project_row:
                    logger.warning(f"项目未找到: {project_id}")
                    return None
                
                # 创建新的知识图谱对象
                knowledge_graph = ProjectKnowledgeGraph(project_root)
                
                # 重建项目上下文
                context_data = dict(zip([col[0] for col in cursor.description], project_row))
                knowledge_graph.context = self._rebuild_project_context(context_data)
                
                # 重建文件和实体信息
                self._rebuild_files_and_entities(conn, project_id, knowledge_graph)
                
                # 重建依赖关系图
                self._rebuild_dependencies(conn, project_id, knowledge_graph)
                
                logger.info(f"从数据库重建项目: {knowledge_graph.context.project_name}")
                
                # 更新访问时间
                conn.execute('UPDATE projects SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?', 
                           (project_id,))
                
                return knowledge_graph
        
        except Exception as e:
            logger.error(f"从数据库加载失败: {e}")
            return None
    
    def _rebuild_project_context(self, context_data: Dict) -> ProjectContext:
        """重建项目上下文"""
        complexity_distribution = json.loads(context_data.get('complexity_distribution', '{}'))
        
        from project_mind import ProjectContext
        return ProjectContext(
            project_root=context_data['project_root'],
            project_name=context_data['project_name'],
            framework_type=context_data['framework_type'],
            main_language=context_data['main_language'],
            architecture_pattern=context_data['architecture_pattern'],
            build_system=context_data['build_system'],
            package_manager=context_data['package_manager'],
            version=context_data['version'],
            total_files=context_data['total_files'],
            total_lines=context_data['total_lines'],
            complexity_distribution=complexity_distribution
        )
    
    def _rebuild_files_and_entities(self, conn: sqlite3.Connection, project_id: str, knowledge_graph):
        """重建文件和实体信息"""
        # 加载文件信息
        cursor = conn.execute('''
            SELECT id, file_path, language, size_bytes, line_count, 
                   file_hash, risk_score, change_frequency, last_modified
            FROM files WHERE project_id = ?
        ''', (project_id,))
        
        file_id_map = {}
        for row in cursor.fetchall():
            file_id, file_path, language, size_bytes, line_count, file_hash, risk_score, change_frequency, last_modified = row
            
            file_node = FileNode(
                file_path=file_path,
                language=language,
                size_bytes=size_bytes,
                line_count=line_count,
                last_modified=datetime.fromisoformat(last_modified) if last_modified else datetime.now(),
                file_hash=file_hash,
                risk_score=risk_score,
                change_frequency=change_frequency
            )
            
            knowledge_graph.files[file_path] = file_node
            file_id_map[file_id] = file_path
        
        # 加载实体信息
        cursor = conn.execute('''
            SELECT file_id, name, entity_type, signature, docstring,
                   line_number, complexity_score, usage_count, last_modified
            FROM entities WHERE project_id = ?
        ''', (project_id,))
        
        for row in cursor.fetchall():
            file_id, name, entity_type, signature, docstring, line_number, complexity_score, usage_count, last_modified = row
            
            file_path = file_id_map.get(file_id)
            if file_path:
                entity = CodeEntity(
                    name=name,
                    entity_type=entity_type,
                    file_path=file_path,
                    line_number=line_number,
                    signature=signature,
                    docstring=docstring,
                    complexity_score=complexity_score,
                    usage_count=usage_count,
                    last_modified=datetime.fromisoformat(last_modified) if last_modified else datetime.now()
                )
                
                entity_key = f"{file_path}:{name}"
                knowledge_graph.entities[entity_key] = entity
                knowledge_graph.files[file_path].entities.append(entity)
    
    def _rebuild_dependencies(self, conn: sqlite3.Connection, project_id: str, knowledge_graph):
        """重建依赖关系图"""
        # 获取文件ID映射
        file_path_map = {}
        cursor = conn.execute('SELECT id, file_path FROM files WHERE project_id = ?', (project_id,))
        for file_id, file_path in cursor.fetchall():
            file_path_map[file_id] = file_path
        
        # 添加节点
        for file_path in knowledge_graph.files.keys():
            knowledge_graph.graph.add_node(file_path, node_type='file')
        
        for entity_key in knowledge_graph.entities.keys():
            knowledge_graph.graph.add_node(entity_key, node_type='entity')
        
        # 加载并重建边
        cursor = conn.execute('''
            SELECT from_file_id, to_file_id, relation_type, strength
            FROM dependencies WHERE project_id = ?
        ''', (project_id,))
        
        for from_file_id, to_file_id, relation_type, strength in cursor.fetchall():
            from_path = file_path_map.get(from_file_id)
            to_path = file_path_map.get(to_file_id)
            
            if from_path and to_path:
                knowledge_graph.graph.add_edge(
                    from_path, to_path,
                    relation_type=relation_type,
                    strength=strength
                )
    
    def update_project_incremental(self, project_root: str) -> bool:
        """增量更新项目信息"""
        # 加载现有项目
        knowledge_graph = self.load_project(project_root)
        if not knowledge_graph:
            logger.warning("项目不存在，执行完整分析")
            knowledge_graph = ProjectKnowledgeGraph(project_root)
            knowledge_graph.analyze_project()
            return self.save_project(knowledge_graph)
        
        # 检查文件变更
        changes_detected = False
        
        for file_path, file_node in knowledge_graph.files.items():
            if Path(file_path).exists():
                current_stat = Path(file_path).stat()
                current_mtime = datetime.fromtimestamp(current_stat.st_mtime)
                
                if current_mtime > file_node.last_modified:
                    logger.info(f"检测到文件变更: {file_path}")
                    # 重新分析这个文件
                    updated_node = knowledge_graph._analyze_single_file(Path(file_path))
                    if updated_node:
                        knowledge_graph.files[file_path] = updated_node
                        changes_detected = True
        
        if changes_detected:
            # 重新构建依赖关系
            knowledge_graph._build_dependency_graph()
            knowledge_graph._calculate_risk_scores()
            knowledge_graph._update_context_statistics()
            
            # 保存更新
            return self.save_project(knowledge_graph)
        
        logger.info("没有检测到文件变更")
        return True
    
    def get_project_list(self) -> List[Dict[str, Any]]:
        """获取所有项目列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT project_name, project_root, framework_type, main_language,
                           total_files, total_lines, last_accessed, created_at
                    FROM projects 
                    WHERE is_active = 1
                    ORDER BY last_accessed DESC
                ''')
                
                projects = []
                for row in cursor.fetchall():
                    projects.append({
                        'project_name': row[0],
                        'project_root': row[1],
                        'framework_type': row[2],
                        'main_language': row[3],
                        'total_files': row[4],
                        'total_lines': row[5],
                        'last_accessed': row[6],
                        'created_at': row[7]
                    })
                
                return projects
        
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            return []
    
    def cleanup_old_data(self, days_old: int = 30):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                # 标记旧项目为非活跃
                cursor = conn.execute('''
                    UPDATE projects SET is_active = 0 
                    WHERE last_accessed < ? AND is_active = 1
                ''', (cutoff_date,))
                
                inactive_count = cursor.rowcount
                
                # 清理相关的缓存文件
                for project_file in self.cache_dir.glob("*.pkl"):
                    if project_file.stat().st_mtime < cutoff_date.timestamp():
                        project_file.unlink()
                        logger.info(f"清理缓存文件: {project_file}")
                
                logger.info(f"标记 {inactive_count} 个项目为非活跃状态")
        
        except Exception as e:
            logger.error(f"清理数据失败: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 项目统计
                cursor = conn.execute('SELECT COUNT(*) FROM projects WHERE is_active = 1')
                active_projects = cursor.fetchone()[0]
                
                cursor = conn.execute('SELECT COUNT(*) FROM projects')
                total_projects = cursor.fetchone()[0]
                
                # 文件统计
                cursor = conn.execute('SELECT COUNT(*) FROM files')
                total_files = cursor.fetchone()[0]
                
                # 实体统计
                cursor = conn.execute('SELECT COUNT(*) FROM entities')
                total_entities = cursor.fetchone()[0]
                
                # 依赖关系统计
                cursor = conn.execute('SELECT COUNT(*) FROM dependencies')
                total_dependencies = cursor.fetchone()[0]
                
                # 数据库大小
                db_size = self.db_path.stat().st_size
                
                # 缓存文件大小
                cache_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.pkl"))
                
                return {
                    'active_projects': active_projects,
                    'total_projects': total_projects,
                    'total_files': total_files,
                    'total_entities': total_entities,
                    'total_dependencies': total_dependencies,
                    'database_size_mb': round(db_size / 1024 / 1024, 2),
                    'cache_size_mb': round(cache_size / 1024 / 1024, 2),
                    'storage_dir': str(self.storage_dir)
                }
        
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}


# 全局项目内存管理器实例
_global_memory_manager = None

def get_memory_manager() -> ProjectMemoryManager:
    """获取全局项目内存管理器实例"""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = ProjectMemoryManager()
    return _global_memory_manager

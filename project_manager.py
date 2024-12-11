import os
import shutil
import json
from datetime import datetime
import streamlit as st
import pandas as pd
from database_manager import DatabaseManager
from model_manager import ModelManager

class ProjectManager:
    def __init__(self, base_path="projects"):
        """Initialize project manager with Streamlit caching"""
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    @st.cache_resource
    def create_project(self, project_name):
        """Create a new project with progress tracking"""
        project_path = os.path.join(self.base_path, project_name)
        
        if os.path.exists(project_path):
            raise ValueError(f"Project {project_name} already exists")

        try:
            with st.spinner("Creating project structure..."):
                # Create project directories
                os.makedirs(project_path)
                os.makedirs(os.path.join(project_path, "models"))
                os.makedirs(os.path.join(project_path, "exports"))
                
                # Initialize database
                db = DatabaseManager(project_path)
                
                # Create project metadata
                metadata = {
                    "name": project_name,
                    "created": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat(),
                    "stats": {
                        "sentences": 0,
                        "concepts": 0,
                        "annotations": 0
                    }
                }
                
                with open(os.path.join(project_path, "metadata.json"), "w") as f:
                    json.dump(metadata, f, indent=2)
                
                st.success(f"Project {project_name} created successfully!")
                return project_path
                
        except Exception as e:
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            st.error(f"Error creating project: {str(e)}")
            raise

    @st.cache_data(ttl=60)  # Cache for 1 minute
    def get_projects(self):
        """Get list of available projects with metadata"""
        if not os.path.exists(self.base_path):
            return []
            
        projects = []
        for project_name in os.listdir(self.base_path):
            project_path = os.path.join(self.base_path, project_name)
            if os.path.isdir(project_path):
                try:
                    # Load project metadata
                    metadata_path = os.path.join(project_path, "metadata.json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    else:
                        metadata = {
                            "name": project_name,
                            "created": "Unknown",
                            "last_modified": "Unknown"
                        }
                    
                    # Get project statistics
                    db = DatabaseManager(project_path)
                    stats = db.get_statistics()
                    
                    projects.append({
                        'name': project_name,
                        'path': project_path,
                        'created': metadata.get('created', 'Unknown'),
                        'last_modified': metadata.get('last_modified', 'Unknown'),
                        'stats': stats
                    })
                except Exception as e:
                    st.warning(f"Error loading project {project_name}: {str(e)}")
                    continue
                    
        return sorted(projects, key=lambda x: x['last_modified'], reverse=True)

    def load_project(self, project_name):
        """Load an existing project"""
        project_path = os.path.join(self.base_path, project_name)
        
        if not os.path.exists(project_path):
            raise ValueError(f"Project {project_name} does not exist")
            
        try:
            with st.spinner(f"Loading project {project_name}..."):
                # Update last modified time
                metadata_path = os.path.join(project_path, "metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    metadata['last_modified'] = datetime.now().isoformat()
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                
                st.success(f"Project {project_name} loaded successfully!")
                return project_path
                
        except Exception as e:
            st.error(f"Error loading project: {str(e)}")
            raise

    def export_project(self, project_name, export_format="csv"):
        """Export project data with progress tracking"""
        project_path = os.path.join(self.base_path, project_name)
        db = DatabaseManager(project_path)
        
        try:
            with st.spinner("Preparing export..."):
                # Get all data
                sentences = db.get_all_sentences()
                annotations = []
                
                progress_bar = st.progress(0)
                for idx, row in sentences.iterrows():
                    sent_annotations = db.get_annotations(row['id'])
                    if not sent_annotations.empty:
                        annotations.append({
                            'sentence_id': row['id'],
                            'sentence': row['sentence'],
                            'annotations': sent_annotations.to_dict('records')
                        })
                    progress_bar.progress((idx + 1) / len(sentences))
                
                # Export to specified format
                export_path = os.path.join(project_path, "exports")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if export_format == "csv":
                    export_file = os.path.join(export_path, f"export_{timestamp}.csv")
                    self._export_to_csv(annotations, export_file)
                else:  # JSON
                    export_file = os.path.join(export_path, f"export_{timestamp}.json")
                    self._export_to_json(annotations, export_file)
                
                progress_bar.empty()
                st.success(f"Export completed: {export_file}")
                return export_file
                
        except Exception as e:
            st.error(f"Export failed: {str(e)}")
            raise

    def _export_to_csv(self, annotations, filepath):
        """Export to CSV format"""
        rows = []
        for item in annotations:
            for ann in item['annotations']:
                rows.append({
                    'sentence_id': item['sentence_id'],
                    'sentence': item['sentence'],
                    'concept': ann['concept'],
                    'begin_idx': ann['begin_idx'],
                    'end_idx': ann['end_idx'],
                    'text': item['sentence'][ann['begin_idx']:ann['end_idx']],
                    'predicted': ann['predicted'],
                    'model_id': ann['model_id'],
                    'status': ['Not Checked', 'Accepted', 'Rejected'][ann['accept_reject_not']]
                })
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)

    def _export_to_json(self, annotations, filepath):
        """Export to JSON format"""
        with open(filepath, 'w') as f:
            json.dump(annotations, f, indent=2)

    def get_project_dashboard(self, project_name):
        """Get dashboard data for a project"""
        project_path = os.path.join(self.base_path, project_name)
        db = DatabaseManager(project_path)
        model_manager = ModelManager(project_path)
        
        stats = db.get_statistics()
        models = model_manager.get_available_models()
        
        return {
            "statistics": stats,
            "models": models,
            "last_export": self._get_last_export(project_path),
            "recent_activity": self._get_recent_activity(project_path)
        }

    def _get_last_export(self, project_path):
        """Get information about the last export"""
        export_path = os.path.join(project_path, "exports")
        if not os.path.exists(export_path):
            return None
            
        exports = [f for f in os.listdir(export_path) if f.startswith("export_")]
        if not exports:
            return None
            
        latest = max(exports, key=lambda f: os.path.getctime(os.path.join(export_path, f)))
        return {
            "filename": latest,
            "timestamp": datetime.fromtimestamp(
                os.path.getctime(os.path.join(export_path, latest))
            ).isoformat(),
            "size_mb": os.path.getsize(os.path.join(export_path, latest)) / (1024 * 1024)
        }

    def _get_recent_activity(self, project_path):
        """Get recent project activity"""
        db = DatabaseManager(project_path)
        
        # Get recent annotations
        with db.get_connection() as conn:
            recent_annotations = pd.read_sql_query(
                """
                SELECT a.*, s.sentence, c.concept
                FROM annotations a
                JOIN sentences s ON a.sentence_id = s.id
                JOIN concepts c ON a.concept_id = c.id
                ORDER BY a.id DESC LIMIT 5
                """,
                conn
            )
        
        return recent_annotations.to_dict('records')

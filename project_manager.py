# project_manager.py

import os
import shutil
import json
from database_manager import DatabaseManager

class ProjectManager:
    def __init__(self, base_path="projects"):
        self.base_path = base_path
        if not os.path.exists(base_path):
            os.makedirs(base_path)
    
    def create_project(self, project_name):
        """Create a new project directory structure"""
        project_path = os.path.join(self.base_path, project_name)
        
        if os.path.exists(project_path):
            raise ValueError(f"Project {project_name} already exists")
        
        # Create project directory structure
        os.makedirs(project_path)
        os.makedirs(os.path.join(project_path, "models"))
        os.makedirs(os.path.join(project_path, "exports"))
        
        # Initialize database
        db = DatabaseManager(project_path)
        
        return project_path
    
    def load_project(self, project_name):
        """Load an existing project"""
        project_path = os.path.join(self.base_path, project_name)
        
        if not os.path.exists(project_path):
            raise ValueError(f"Project {project_name} does not exist")
        
        db = DatabaseManager(project_path)
        return project_path
    
    def get_projects(self):
        """Get list of all projects"""
        if not os.path.exists(self.base_path):
            return []
        return [d for d in os.listdir(self.base_path) 
                if os.path.isdir(os.path.join(self.base_path, d))]
    
    def export_project(self, project_name, export_format="csv"):
        """Export project annotations"""
        project_path = os.path.join(self.base_path, project_name)
        db = DatabaseManager(project_path)
        
        sentences = db.get_all_sentences()
        annotations = []
        
        for _, row in sentences.iterrows():
            sentence_annotations = db.get_annotations(row['id'])
            if not sentence_annotations.empty:
                annotations.append({
                    'sentence_id': row['id'],
                    'sentence': row['sentence'],
                    'annotations': sentence_annotations.to_dict('records')
                })
        
        # Export to specified format
        export_path = os.path.join(project_path, "exports")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == "csv":
            export_file = os.path.join(export_path, f"export_{timestamp}.csv")
            self._export_to_csv(annotations, export_file)
        elif export_format == "json":
            export_file = os.path.join(export_path, f"export_{timestamp}.json")
            self._export_to_json(annotations, export_file)
        
        return export_file
    
    def _export_to_csv(self, annotations, filepath):
        """Export annotations to CSV format"""
        rows = []
        for item in annotations:
            for ann in item['annotations']:
                rows.append({
                    'sentence_id': item['sentence_id'],
                    'sentence': item['sentence'],
                    'concept': ann['concept'],
                    'begin_idx': ann['begin_idx'],
                    'end_idx': ann['end_idx'],
                    'predicted': ann['predicted'],
                    'accept_reject_not': ann['accept_reject_not']
                })
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
    
    def _export_to_json(self, annotations, filepath):
        """Export annotations to JSON format"""
        with open(filepath, 'w') as f:
            json.dump(annotations, f, indent=2)

import sqlite3
import os
from pathlib import Path

class AnnotationProject:
    """
    Handles all database operations for the annotation project.
    Manages sentences, concepts, annotations, and their relationships.
    """
    def __init__(self, project_name: str, base_path: str = "projects/"):
        """
        Initialize annotation project and database
        
        Args:
            project_name: Name of the project
            base_path: Base directory for project storage
        """
        self.project_name = project_name
        self.base_path = Path(base_path)
        self.project_path = self.base_path / project_name
        
        # Create project directory structure
        self._create_project_structure()
        
        # Initialize database
        self.db_path = self.project_path / f"{project_name}.db"
        self._init_database()

    def _create_project_structure(self):
        """Create necessary project directories"""
        os.makedirs(self.project_path, exist_ok=True)
        os.makedirs(self.project_path / "models", exist_ok=True)
        os.makedirs(self.project_path / "files", exist_ok=True)

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # Create sentences table
            c.execute("""
                CREATE TABLE IF NOT EXISTS sentences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence TEXT NOT NULL
                )
            """)
            
            # Create sentence attributes table
            c.execute("""
                CREATE TABLE IF NOT EXISTS sentence_attributes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_id INTEGER NOT NULL,
                    attr_name TEXT NOT NULL,
                    attr_value TEXT NOT NULL,
                    FOREIGN KEY(sentence_id) REFERENCES sentences(id)
                )
            """)
            
            # Create concepts table
            c.execute("""
                CREATE TABLE IF NOT EXISTS concepts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT NOT NULL,
                    color TEXT NOT NULL
                )
            """)
            
            # Create annotations table
            c.execute("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_id INTEGER NOT NULL,
                    concept_id INTEGER NOT NULL,
                    begin_idx INTEGER NOT NULL,
                    end_idx INTEGER NOT NULL,
                    predicted BOOLEAN NOT NULL,
                    model_id INTEGER NOT NULL,
                    accept_reject_not INTEGER NOT NULL,
                    FOREIGN KEY(sentence_id) REFERENCES sentences(id),
                    FOREIGN KEY(concept_id) REFERENCES concepts(id)
                )
            """)

    def add_sentences(self, sentence: str, attributes: list = None):
        """
        Add a new sentence and its attributes to the database
        
        Args:
            sentence: The sentence text
            attributes: List of (attribute_name, attribute_value) tuples
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO sentences (sentence) VALUES (?)", (sentence,))
            sentence_id = c.lastrowid
            
            if attributes:
                for attr_name, attr_value in attributes:
                    c.execute("""
                        INSERT INTO sentence_attributes (sentence_id, attr_name, attr_value)
                        VALUES (?, ?, ?)
                    """, (sentence_id, attr_name, attr_value))

    def add_concepts(self, concept: str, color: str):
        """
        Add a new concept with color to the database
        
        Args:
            concept: Concept name
            color: Color code (hex)
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO concepts (concept, color) VALUES (?, ?)", (concept, color))

    def set_annotations(self, sentence_id: int, concept_id: int, begin_idx: int, 
                       end_idx: int, model_id: int, predict: bool, accept_reject_not: int):
        """
        Add or update an annotation in the database
        
        Args:
            sentence_id: ID of the sentence
            concept_id: ID of the concept
            begin_idx: Start index of annotation
            end_idx: End index of annotation
            model_id: ID of the model (0 for manual annotations)
            predict: Whether this is a model prediction
            accept_reject_not: Annotation status (0=reject, 1=accept, 2=not reviewed)
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            # Check if annotation exists
            c.execute("""
                SELECT id FROM annotations 
                WHERE sentence_id = ? AND concept_id = ? AND begin_idx = ? AND end_idx = ?
            """, (sentence_id, concept_id, begin_idx, end_idx))
            
            existing = c.fetchone()
            
            if existing:
                c.execute("""
                    UPDATE annotations 
                    SET predicted = ?, model_id = ?, accept_reject_not = ?
                    WHERE id = ?
                """, (predict, model_id, accept_reject_not, existing[0]))
            else:
                c.execute("""
                    INSERT INTO annotations 
                    (sentence_id, concept_id, begin_idx, end_idx, predicted, model_id, accept_reject_not)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sentence_id, concept_id, begin_idx, end_idx, predict, model_id, accept_reject_not))

    def get_all_sentences(self):
        """Get all sentences from database"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM sentences")
            return c.fetchall()

    def get_all_concepts(self):
        """Get all concepts from database"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM concepts")
            return c.fetchall()

    def get_sentence_attributes(self, sentence_id: int):
        """Get attributes for a specific sentence"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT attr_name, attr_value 
                FROM sentence_attributes 
                WHERE sentence_id = ?
            """, (sentence_id,))
            return c.fetchall()

    def get_annotations_from_sentence(self, sentence_id: int):
        """Get all annotations for a specific sentence"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM annotations WHERE sentence_id = ?", (sentence_id,))
            return c.fetchall()

    def get_concepts(self, concept_id: int):
        """Get concept name by ID"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT concept FROM concepts WHERE id = ?", (concept_id,))
            result = c.fetchone()
            return result[0] if result else None

    def get_concepts_color(self, concept_id: int):
        """Get concept color by ID"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT color FROM concepts WHERE id = ?", (concept_id,))
            result = c.fetchone()
            return result[0] if result else None

    def delete_annotation(self, annotation_id: int):
        """Delete a specific annotation"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))

    def export_annotations(self):
        """Export all annotations in training data format"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT s.sentence, a.begin_idx, a.end_idx, c.concept
                FROM annotations a
                JOIN sentences s ON a.sentence_id = s.id
                JOIN concepts c ON a.concept_id = c.id
                WHERE a.accept_reject_not = 1
                ORDER BY s.id
            """)
            return c.fetchall()

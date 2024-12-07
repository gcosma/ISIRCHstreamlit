# database_manager.py

import sqlite3
import os
import pandas as pd

class DatabaseManager:
    def __init__(self, project_path):
        self.db_path = os.path.join(project_path, "project.db")
        self.initialize_database()
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create sentences table
        c.execute("""CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence TEXT NOT NULL
        )""")
        
        # Create sentence attributes table
        c.execute("""CREATE TABLE IF NOT EXISTS sen_attr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sen_id INTEGER NOT NULL,
            attr_name TEXT NOT NULL,
            attr_value TEXT NOT NULL,
            FOREIGN KEY(sen_id) REFERENCES sentences(id)
        )""")
        
        # Create concepts table
        c.execute("""CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT NOT NULL,
            color TEXT NOT NULL
        )""")
        
        # Create annotations table
        c.execute("""CREATE TABLE IF NOT EXISTS annotations (
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
        )""")
        
        conn.commit()
        conn.close()
    
    def add_sentence(self, sentence, attributes=None):
        """Add a new sentence with optional attributes"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("INSERT INTO sentences (sentence) VALUES (?)", (sentence,))
        sentence_id = c.lastrowid
        
        if attributes:
            for name, value in attributes.items():
                c.execute(
                    "INSERT INTO sen_attr (sen_id, attr_name, attr_value) VALUES (?, ?, ?)",
                    (sentence_id, name, value)
                )
        
        conn.commit()
        conn.close()
        return sentence_id
    
    def add_concept(self, concept, color):
        """Add a new concept with color"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("INSERT INTO concepts (concept, color) VALUES (?, ?)", (concept, color))
        concept_id = c.lastrowid
        
        conn.commit()
        conn.close()
        return concept_id
    
    def get_all_sentences(self):
        """Retrieve all sentences with their IDs"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM sentences", conn)
        conn.close()
        return df
    
    def get_all_concepts(self):
        """Retrieve all concepts with their colors"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM concepts", conn)
        conn.close()
        return df
    
    def add_annotation(self, sentence_id, concept_id, begin_idx, end_idx, predicted=False, model_id=0):
        """Add a new annotation"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO annotations 
            (sentence_id, concept_id, begin_idx, end_idx, predicted, model_id, accept_reject_not)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (sentence_id, concept_id, begin_idx, end_idx, predicted, model_id))
        
        conn.commit()
        conn.close()
    
    def get_annotations(self, sentence_id):
        """Get all annotations for a sentence"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            """
            SELECT a.*, c.concept, c.color
            FROM annotations a
            JOIN concepts c ON a.concept_id = c.id
            WHERE a.sentence_id = ?
            """, 
            conn,
            params=(sentence_id,)
        )
        conn.close()
        return df

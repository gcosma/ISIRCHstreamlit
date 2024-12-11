import sqlite3
import pandas as pd
import streamlit as st
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, project_path):
        """Initialize database connection with error handling"""
        self.db_path = os.path.join(project_path, "project.db")
        self.initialize_database()
        
    def get_connection(self):
        """Get database connection with context management"""
        return sqlite3.connect(self.db_path)
        
    @st.cache_resource
    def initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            with self.get_connection() as conn:
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
                    CREATE TABLE IF NOT EXISTS sen_attr (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sen_id INTEGER NOT NULL,
                        attr_name TEXT NOT NULL,
                        attr_value TEXT NOT NULL,
                        FOREIGN KEY(sen_id) REFERENCES sentences(id)
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
                
                conn.commit()
                
        except sqlite3.Error as e:
            st.error(f"Database initialization error: {str(e)}")
            raise

    def add_sentence(self, sentence, attributes=None):
        """Add a new sentence with optional attributes"""
        try:
            with self.get_connection() as conn:
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
                return sentence_id
                
        except sqlite3.Error as e:
            st.error(f"Error adding sentence: {str(e)}")
            raise

    def add_concept(self, concept, color):
        """Add a new concept"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO concepts (concept, color) VALUES (?, ?)", 
                         (concept, color))
                concept_id = c.lastrowid
                conn.commit()
                return concept_id
                
        except sqlite3.Error as e:
            st.error(f"Error adding concept: {str(e)}")
            raise

    def get_all_sentences(self):
        """Get all sentences as a pandas DataFrame"""
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query("SELECT * FROM sentences", conn)
        except sqlite3.Error as e:
            st.error(f"Error retrieving sentences: {str(e)}")
            return pd.DataFrame()

    def get_all_concepts(self):
        """Get all concepts as a pandas DataFrame"""
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query("SELECT * FROM concepts", conn)
        except sqlite3.Error as e:
            st.error(f"Error retrieving concepts: {str(e)}")
            return pd.DataFrame()

    def get_annotations(self, sentence_id):
        """Get annotations for a sentence"""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT a.*, c.concept, c.color
                    FROM annotations a
                    JOIN concepts c ON a.concept_id = c.id
                    WHERE a.sentence_id = ?
                """
                return pd.read_sql_query(query, conn, params=(sentence_id,))
        except sqlite3.Error as e:
            st.error(f"Error retrieving annotations: {str(e)}")
            return pd.DataFrame()

    def add_annotation(self, sentence_id, concept_id, begin_idx, end_idx, 
                      predicted=False, model_id=0, accept_reject_not=0):
        """Add or update an annotation"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                
                # Check for existing annotation
                c.execute("""
                    SELECT id FROM annotations 
                    WHERE sentence_id = ? AND concept_id = ? 
                    AND begin_idx = ? AND end_idx = ?
                """, (sentence_id, concept_id, begin_idx, end_idx))
                
                existing = c.fetchone()
                
                if existing:
                    # Update existing annotation
                    c.execute("""
                        UPDATE annotations 
                        SET predicted = ?, model_id = ?, accept_reject_not = ?
                        WHERE id = ?
                    """, (predicted, model_id, accept_reject_not, existing[0]))
                else:
                    # Insert new annotation
                    c.execute("""
                        INSERT INTO annotations 
                        (sentence_id, concept_id, begin_idx, end_idx, 
                         predicted, model_id, accept_reject_not)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (sentence_id, concept_id, begin_idx, end_idx,
                         predicted, model_id, accept_reject_not))
                
                conn.commit()
                
        except sqlite3.Error as e:
            st.error(f"Error managing annotation: {str(e)}")
            raise

    def delete_annotation(self, annotation_id):
        """Delete an annotation"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
                conn.commit()
        except sqlite3.Error as e:
            st.error(f"Error deleting annotation: {str(e)}")
            raise

    def get_statistics(self):
        """Get project statistics"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                
                stats = {
                    'total_sentences': c.execute("SELECT COUNT(*) FROM sentences").fetchone()[0],
                    'total_concepts': c.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
                    'total_annotations': c.execute("SELECT COUNT(*) FROM annotations").fetchone()[0],
                    'manual_annotations': c.execute(
                        "SELECT COUNT(*) FROM annotations WHERE predicted = 0"
                    ).fetchone()[0],
                    'predicted_annotations': c.execute(
                        "SELECT COUNT(*) FROM annotations WHERE predicted = 1"
                    ).fetchone()[0],
                    'accepted_predictions': c.execute(
                        "SELECT COUNT(*) FROM annotations WHERE predicted = 1 AND accept_reject_not = 1"
                    ).fetchone()[0]
                }
                
                return stats
                
        except sqlite3.Error as e:
            st.error(f"Error getting statistics: {str(e)}")
            return {}

# app.py

import streamlit as st
import pandas as pd
from project_manager import ProjectManager
from database_manager import DatabaseManager
from model_manager import ModelManager
import os

class StreamlitSACAT:
    def __init__(self):
        st.set_page_config(page_title="SACAT", layout="wide")
        
        # Initialize session state
        if 'project_manager' not in st.session_state:
            st.session_state.project_manager = ProjectManager()
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'current_sentence_index' not in st.session_state:
            st.session_state.current_sentence_index = 0
            
        self.setup_session_state()
    
    def setup_session_state(self):
        """Initialize additional session state variables"""
        if st.session_state.current_project:
            if 'db_manager' not in st.session_state:
                st.session_state.db_manager = DatabaseManager(st.session_state.current_project)
            if 'model_manager' not in st.session_state:
                st.session_state.model_manager = ModelManager(st.session_state.current_project)
    
    def main(self):
        st.title("SACAT - Semi-Automated Concept Annotation Tool")
        
        # Sidebar navigation
        self.sidebar_navigation()
        
        # Main content area
        if st.session_state.current_project:
            self.show_annotation_interface()
        else:
            st.write("Please create or load a project to begin")
    
    def sidebar_navigation(self):
        with st.sidebar:
            st.header("Project Management")
            
            # Project selection
            project_action = st.radio(
                "Select Action",
                ["Create New Project", "Load Project", "Export Annotations"]
            )
            
            if project_action == "Create New Project":
                self.create_project_ui()
            elif project_action == "Load Project":
                self.load_project_ui()
            elif project_action == "Export Annotations":
                self.export_annotations_ui()
            
            # Model management (if project is loaded)
            if st.session_state.current_project:
                st.header("Model Management")
                if st.button("Train New Model"):
                    self.train_model_ui()
                if st.button("Run Predictions"):
                    self.run_predictions_ui()
    
    def show_annotation_interface(self):
        """Main annotation interface"""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("Text Annotation")
            
            # Sentence navigation
            sentences = st.session_state.db_manager.get_all_sentences()
            if not sentences.empty:    # <-- This line was misaligned, now fixed
                # Navigation controls
                cols = st.columns([1, 3, 1])
                with cols[0]:
                    if st.button("Previous") and st.session_state.current_sentence_index > 0:
                        st.session_state.current_sentence_index -= 1
                        st.rerun()
                
                with cols[1]:
                    sentence_index = st.selectbox(
                        "Select Sentence",
                        range(len(sentences)),
                        index=st.session_state.current_sentence_index,
                        format_func=lambda x: f"Sentence {x + 1} of {len(sentences)}"
                    )
                    st.session_state.current_sentence_index = sentence_index
                
                with cols[2]:
                    if st.button("Next") and st.session_state.current_sentence_index < len(sentences) - 1:
                        st.session_state.current_sentence_index += 1
                        st.rerun()

                # Display current sentence
                current_sentence = sentences.iloc[st.session_state.current_sentence_index]
                
                # Custom component for text selection and annotation
                text_container = st.container()
                with text_container:
                    st.markdown("### Current Sentence")
                    
                    # Get existing annotations for this sentence
                    annotations = st.session_state.db_manager.get_annotations(current_sentence['id'])
                    
                    # Display text with annotations using HTML/CSS
                    html_text = self.render_annotated_text(current_sentence['sentence'], annotations)
                    st.markdown(html_text, unsafe_allow_html=True)
                    
                    # Text selection handling
                    if 'selected_text' not in st.session_state:
                        st.session_state.selected_text = None
                    
                    # JavaScript for text selection
                    st.markdown("""
                        <script>
                            document.addEventListener('mouseup', function() {
                                const selection = window.getSelection();
                                const selectedText = selection.toString();
                                if (selectedText) {
                                    // Send selection to Streamlit
                                    window.parent.postMessage({
                                        type: 'text_selected',
                                        text: selectedText,
                                        start: selection.anchorOffset,
                                        end: selection.focusOffset
                                    }, '*');
                                }
                            });
                        </script>
                    """, unsafe_allow_html=True)
            
            else:
                st.write("No sentences available. Please add some sentences to the project.")

        with col2:
            st.header("Concepts")
            
            # Add new concept
            with st.form("new_concept_form"):
                new_concept = st.text_input("New Concept Name")
                concept_color = st.color_picker("Choose Color", "#00ff00")
                submit_concept = st.form_submit_button("Add Concept")
                
                if submit_concept and new_concept:
                    st.session_state.db_manager.add_concept(new_concept, concept_color)
                    st.rerun()
            
            # Display existing concepts
            concepts = st.session_state.db_manager.get_all_concepts()
            if not concepts.empty:
                st.markdown("### Existing Concepts")
                for _, concept in concepts.iterrows():
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(
                            f'<div style="background-color: {concept["color"]}; padding: 5px; border-radius: 5px;">'
                            f'{concept["concept"]}</div>',
                            unsafe_allow_html=True
                        )
                    with cols[1]:
                        if st.button("Select", key=f"concept_{concept['id']}"):
                            if hasattr(st.session_state, 'selected_text'):
                                self.add_annotation(
                                    current_sentence['id'],
                                    concept['id'],
                                    st.session_state.selected_text
                                )
                                st.rerun()
    
    def render_annotated_text(self, text, annotations):
        """Render text with colored annotations"""
        if annotations.empty:
            return f"<p>{text}</p>"
        
        # Sort annotations by start position
        annotations = annotations.sort_values('begin_idx')
        
        html_parts = []
        last_idx = 0
        
        for _, ann in annotations.iterrows():
            # Add text before annotation
            if ann['begin_idx'] > last_idx:
                html_parts.append(text[last_idx:ann['begin_idx']])
            
            # Add annotated text
            annotated_text = text[ann['begin_idx']:ann['end_idx']]
            html_parts.append(
                f'<span style="background-color: {ann["color"]};">{annotated_text}</span>'
            )
            
            last_idx = ann['end_idx']
        
        # Add remaining text
        if last_idx < len(text):
            html_parts.append(text[last_idx:])
        
        return "<p>" + "".join(html_parts) + "</p>"
    
    def add_annotation(self, sentence_id, concept_id, selection_info):
        """Add new annotation to database"""
        st.session_state.db_manager.add_annotation(
            sentence_id,
            concept_id,
            selection_info['start'],
            selection_info['end']
        )
    
    def create_project_ui(self):
        """UI for creating new project"""
        st.sidebar.subheader("Create New Project")
        project_name = st.sidebar.text_input("Project Name")
        if st.sidebar.button("Create Project"):
            if project_name:
                try:
                    project_path = st.session_state.project_manager.create_project(project_name)
                    st.session_state.current_project = project_path
                    st.session_state.db_manager = DatabaseManager(project_path)
                    st.session_state.model_manager = ModelManager(project_path)
                    st.sidebar.success(f"Project {project_name} created successfully!")
                    st.rerun()
                except ValueError as e:
                    st.sidebar.error(str(e))
    
    def load_project_ui(self):
        """UI for loading existing project"""
        st.sidebar.subheader("Load Project")
        projects = st.session_state.project_manager.get_projects()
        if projects:
            selected_project = st.sidebar.selectbox("Select Project", projects)
            if st.sidebar.button("Load Project"):
                try:
                    project_path = st.session_state.project_manager.load_project(selected_project)
                    st.session_state.current_project = project_path
                    st.session_state.db_manager = DatabaseManager(project_path)
                    st.session_state.model_manager = ModelManager(project_path)
                    st.sidebar.success(f"Project {selected_project} loaded successfully!")
                    st.rerun()
                except ValueError as e:
                    st.sidebar.error(str(e))
        else:
            st.sidebar.write("No projects available")

    def train_model_ui(self):
        """UI for training new model"""
        if st.session_state.current_project:
            with st.spinner("Training model..."):
                sentences = st.session_state.db_manager.get_all_sentences()
                annotations = [
                    st.session_state.db_manager.get_annotations(sen_id) 
                    for sen_id in sentences['id']
                ]
                
                training_data = st.session_state.model_manager.create_training_data(
                    sentences['sentence'],
                    annotations
                )
                
                model_path = st.session_state.model_manager.train_model(
                    training_data,
                    f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                st.success(f"Model trained successfully and saved to {model_path}")

    def export_annotations_ui(self):
        """UI for exporting annotations"""
        if st.session_state.current_project:
            st.sidebar.subheader("Export Annotations")
            export_format = st.sidebar.selectbox(
                "Export Format",
                ["CSV", "JSON"]
            )
            
            if st.sidebar.button("Export"):
                try:
                    export_file = st.session_state.project_manager.export_project(
                        os.path.basename(st.session_state.current_project),
                        export_format.lower()
                    )
                    st.sidebar.success(f"Annotations exported to {export_file}")
                except Exception as e:
                    st.sidebar.error(f"Export failed: {str(e)}")
        else:
            st.sidebar.write("Please load a project first")

if __name__ == "__main__":
    app = StreamlitSACAT()
    app.main()

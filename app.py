# app.py

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from project_manager import ProjectManager
from database_manager import DatabaseManager
from model_manager import ModelManager

# Ensure required directories exist
os.makedirs('projects', exist_ok=True)
os.makedirs('static', exist_ok=True)

class StreamlitSACAT:
    def __init__(self):
        st.set_page_config(
            page_title="SACAT", 
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Initialize session state
        self.init_session_state()
            
    def init_session_state(self):
        """Initialize session state variables"""
        if 'project_manager' not in st.session_state:
            st.session_state.project_manager = ProjectManager()
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'current_sentence_index' not in st.session_state:
            st.session_state.current_sentence_index = 0
        if 'selected_text' not in st.session_state:
            st.session_state.selected_text = None
            
        # Initialize managers if project is loaded
        if st.session_state.current_project:
            if 'db_manager' not in st.session_state:
                st.session_state.db_manager = DatabaseManager(st.session_state.current_project)
            if 'model_manager' not in st.session_state:
                st.session_state.model_manager = ModelManager(st.session_state.current_project)
    
    def main(self):
        st.title("SACAT - Semi-Automated Concept Annotation Tool")
        
        # Add project info if loaded
        if st.session_state.current_project:
            st.caption(f"Current Project: {os.path.basename(st.session_state.current_project)}")
        
        # Sidebar navigation
        self.sidebar_navigation()
        
        # Main content area
        if st.session_state.current_project:
            self.show_annotation_interface()
        else:
            st.info("Please create or load a project to begin")
            self.show_welcome_screen()
    
    def show_welcome_screen(self):
        """Display welcome information when no project is loaded"""
        st.markdown("""
        ### Welcome to SACAT
        
        SACAT (Semi-Automated Concept Annotation Tool) helps you:
        - Annotate text with concepts
        - Train models to assist with annotation
        - Export annotations for analysis
        
        To get started:
        1. Create a new project, or
        2. Load an existing project
        """)
    
    def sidebar_navigation(self):
        with st.sidebar:
            st.header("Project Management")
            
            # Project selection
            project_action = st.radio(
                "Select Action",
                ["Create New Project", "Load Project", "Export Annotations"],
                key="project_action"
            )
            
            st.divider()
            
            if project_action == "Create New Project":
                self.create_project_ui()
            elif project_action == "Load Project":
                self.load_project_ui()
            elif project_action == "Export Annotations":
                self.export_annotations_ui()
            
            # Model management (if project is loaded)
            if st.session_state.current_project:
                st.header("Model Management")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Train Model", use_container_width=True):
                        self.train_model_ui()
                with col2:
                    if st.button("Make Predictions", use_container_width=True):
                        self.run_predictions_ui()

    def show_annotation_interface(self):
        """Main annotation interface"""
        # Create two columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.show_text_annotation_interface()
        
        with col2:
            self.show_concept_interface()

    def show_text_annotation_interface(self):
        """Show text annotation interface in left column"""
        st.header("Text Annotation")
        
        # Get sentences
        sentences = st.session_state.db_manager.get_all_sentences()
        if sentences.empty:
            st.warning("No sentences available. Please add sentences to the project.")
            self.show_sentence_upload_interface()
            return
            
        # Navigation controls
        self.show_navigation_controls(sentences)
        
        # Display current sentence and annotations
        current_sentence = sentences.iloc[st.session_state.current_sentence_index]
        self.show_current_sentence(current_sentence)

    def show_navigation_controls(self, sentences):
        """Show sentence navigation controls"""
        cols = st.columns([1, 3, 1])
        with cols[0]:
            if st.button("⬅️ Previous", use_container_width=True) and st.session_state.current_sentence_index > 0:
                st.session_state.current_sentence_index -= 1
                st.rerun()
        
        with cols[1]:
            st.selectbox(
                "Select Sentence",
                range(len(sentences)),
                index=st.session_state.current_sentence_index,
                format_func=lambda x: f"Sentence {x + 1} of {len(sentences)}",
                key="sentence_selector",
                on_change=self.on_sentence_selected
            )
        
        with cols[2]:
            if st.button("Next ➡️", use_container_width=True) and st.session_state.current_sentence_index < len(sentences) - 1:
                st.session_state.current_sentence_index += 1
                st.rerun()

    def show_current_sentence(self, sentence):
        """Show current sentence and handle annotations"""
        with st.container():
            st.markdown("### Current Sentence")
            
            # Get existing annotations
            annotations = st.session_state.db_manager.get_annotations(sentence['id'])
            
            # Create a container for the annotated text
            text_container = st.container()
            with text_container:
                # Display annotated text
                html_text = self.render_annotated_text(sentence['sentence'], annotations)
                st.markdown(html_text, unsafe_allow_html=True)
                
                # Add text selection handling
                self.add_text_selection_handler()

    def show_concept_interface(self):
        """Show concept interface in right column"""
        st.header("Concepts")
        
        # Add new concept form
        with st.form("new_concept_form", clear_on_submit=True):
            new_concept = st.text_input("New Concept Name")
            concept_color = st.color_picker("Choose Color", "#00ff00")
            
            if st.form_submit_button("Add Concept", use_container_width=True):
                if new_concept:
                    st.session_state.db_manager.add_concept(new_concept, concept_color)
                    st.rerun()
                else:
                    st.warning("Please enter a concept name")
        
        # Display existing concepts
        concepts = st.session_state.db_manager.get_all_concepts()
        if not concepts.empty:
            st.markdown("### Existing Concepts")
            
            for _, concept in concepts.iterrows():
                with st.container():
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(
                            f'<div style="background-color: {concept["color"]}; '
                            f'padding: 8px; border-radius: 5px; margin: 2px 0;">'
                            f'{concept["concept"]}</div>',
                            unsafe_allow_html=True
                        )
                    with cols[1]:
                        if st.button("Select", key=f"concept_{concept['id']}", 
                                   use_container_width=True):
                            if st.session_state.selected_text:
                                self.add_annotation(
                                    st.session_state.current_sentence['id'],
                                    concept['id'],
                                    st.session_state.selected_text
                                )
                                st.rerun()
                            else:
                                st.warning("Please select text to annotate")
        def render_annotated_text(self, text, annotations):
        """Render text with colored annotations and improved styling"""
        if annotations.empty:
            return f'<div style="font-size: 1.2em; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">{text}</div>'
        
        # Sort annotations by start position
        annotations = annotations.sort_values('begin_idx')
        
        html_parts = []
        last_idx = 0
        
        for _, ann in annotations.iterrows():
            # Add text before annotation
            if ann['begin_idx'] > last_idx:
                html_parts.append(text[last_idx:ann['begin_idx']])
            
            # Add annotated text with improved styling
            annotated_text = text[ann['begin_idx']:ann['end_idx']]
            html_parts.append(
                f'<span style="background-color: {ann["color"]}; '
                f'padding: 2px 4px; border-radius: 3px; margin: 0 2px;">'
                f'{annotated_text}</span>'
            )
            
            last_idx = ann['end_idx']
        
        # Add remaining text
        if last_idx < len(text):
            html_parts.append(text[last_idx:])
        
        return f'<div style="font-size: 1.2em; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">' + "".join(html_parts) + '</div>'

    def add_text_selection_handler(self):
        """Add JavaScript for text selection with improved handling"""
        st.markdown("""
            <script>
                const streamlit = window.parent.streamlit;
                document.addEventListener('mouseup', function() {
                    const selection = window.getSelection();
                    const selectedText = selection.toString().trim();
                    
                    if (selectedText) {
                        const range = selection.getRangeAt(0);
                        const start = range.startOffset;
                        const end = range.endOffset;
                        
                        // Send selection to Streamlit
                        streamlit.setComponentValue({
                            type: 'text_selected',
                            text: selectedText,
                            start: start,
                            end: end
                        });
                    }
                });
            </script>
        """, unsafe_allow_html=True)

    def add_annotation(self, sentence_id, concept_id, selection_info):
        """Add new annotation with validation"""
        try:
            if not selection_info or 'start' not in selection_info or 'end' not in selection_info:
                st.error("Invalid text selection")
                return
                
            st.session_state.db_manager.add_annotation(
                sentence_id=sentence_id,
                concept_id=concept_id,
                begin_idx=selection_info['start'],
                end_idx=selection_info['end'],
                predicted=False,
                model_id=0,
                accept_reject_not=0
            )
            
            # Clear selection after successful annotation
            st.session_state.selected_text = None
            
        except Exception as e:
            st.error(f"Error adding annotation: {str(e)}")

    def create_project_ui(self):
        """Enhanced UI for creating new project"""
        st.sidebar.subheader("Create New Project")
        
        with st.sidebar.form("create_project_form"):
            project_name = st.text_input(
                "Project Name",
                help="Enter a unique name for your project"
            )
            
            submit = st.form_submit_button("Create Project", use_container_width=True)
            
            if submit:
                if not project_name:
                    st.error("Please enter a project name")
                    return
                    
                try:
                    project_path = st.session_state.project_manager.create_project(project_name)
                    st.session_state.current_project = project_path
                    st.session_state.db_manager = DatabaseManager(project_path)
                    st.session_state.model_manager = ModelManager(project_path)
                    st.success(f"Project '{project_name}' created successfully!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    def load_project_ui(self):
        """Enhanced UI for loading projects"""
        st.sidebar.subheader("Load Project")
        
        projects = st.session_state.project_manager.get_projects()
        if not projects:
            st.sidebar.warning("No projects available")
            return
            
        selected_project = st.sidebar.selectbox(
            "Select Project",
            projects,
            format_func=lambda x: f"{x} ({self.get_project_stats(x)})"
        )
        
        if st.sidebar.button("Load Project", use_container_width=True):
            try:
                project_path = st.session_state.project_manager.load_project(selected_project)
                st.session_state.current_project = project_path
                st.session_state.db_manager = DatabaseManager(project_path)
                st.session_state.model_manager = ModelManager(project_path)
                st.success(f"Project '{selected_project}' loaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading project: {str(e)}")

    def get_project_stats(self, project_name):
        """Get project statistics for display"""
        try:
            stats = st.session_state.project_manager.get_project_dashboard(project_name)
            return f"{stats['statistics']['total_sentences']} sentences, {stats['statistics']['total_annotations']} annotations"
        except:
            return "No stats available"

    def train_model_ui(self):
        """Enhanced UI for model training"""
        if not st.session_state.current_project:
            st.error("Please load a project first")
            return
            
        # Check if we have enough data
        sentences = st.session_state.db_manager.get_all_sentences()
        if len(sentences) < 10:  # Minimum required sentences
            st.warning("Not enough training data. Please add more annotated sentences (minimum 10 required).")
            return
            
        try:
            with st.spinner("Preparing training data..."):
                annotations = [
                    st.session_state.db_manager.get_annotations(sen_id) 
                    for sen_id in sentences['id']
                ]
                
                # Check if we have annotations
                if not any(not ann.empty for ann in annotations):
                    st.warning("No annotations found. Please add some annotations before training.")
                    return
                
                training_data = st.session_state.model_manager.create_training_data(
                    sentences['sentence'],
                    annotations
                )
                
                model_name = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                with st.status("Training model...") as status:
                    model_path = st.session_state.model_manager.train_model(
                        training_data,
                        model_name
                    )
                    status.update(label="Model training complete!", state="complete")
                
                st.success(f"Model trained and saved successfully!")
                
        except Exception as e:
            st.error(f"Error during model training: {str(e)}")

    def run_predictions_ui(self):
        """UI for running predictions"""
        if not st.session_state.current_project:
            st.error("Please load a project first")
            return
            
        try:
            # Get available models
            models = st.session_state.model_manager.get_available_models()
            if not models:
                st.warning("No trained models available. Please train a model first.")
                return
                
            # Select model
            selected_model = st.selectbox(
                "Select Model",
                models,
                format_func=lambda x: f"{x['name']} (created: {x['created'][:10]})"
            )
            
            if st.button("Run Predictions"):
                with st.spinner("Making predictions..."):
                    # Load model
                    st.session_state.model_manager.load_model(selected_model['name'])
                    
                    # Get unannotated sentences
                    sentences = st.session_state.db_manager.get_all_sentences()
                    
                    progress_bar = st.progress(0)
                    for idx, row in sentences.iterrows():
                        predictions = st.session_state.model_manager.predict(row['sentence'])
                        
                        # Add predictions to database
                        for pred in predictions:
                            if pred['score'] > 0.5:  # Confidence threshold
                                st.session_state.db_manager.add_annotation(
                                    sentence_id=row['id'],
                                    concept_id=pred['concept_id'],
                                    begin_idx=pred['begin_idx'],
                                    end_idx=pred['end_idx'],
                                    predicted=True,
                                    model_id=selected_model['name'],
                                    accept_reject_not=0
                                )
                        
                        progress_bar.progress((idx + 1) / len(sentences))
                    
                    st.success("Predictions complete!")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error making predictions: {str(e)}")

    def export_annotations_ui(self):
        """Enhanced UI for exporting annotations"""
        if not st.session_state.current_project:
            st.sidebar.warning("Please load a project first")
            return
            
        st.sidebar.subheader("Export Annotations")
        
        with st.sidebar.form("export_form"):
            export_format = st.selectbox(
                "Export Format",
                ["CSV", "JSON"],
                help="Choose the format for your export"
            )
            
            include_predictions = st.checkbox(
                "Include Predictions",
                value=True,
                help="Include model predictions in export"
            )
            
            if st.form_submit_button("Export", use_container_width=True):
                try:
                    with st.spinner("Exporting annotations..."):
                        export_file = st.session_state.project_manager.export_project(
                            os.path.basename(st.session_state.current_project),
                            export_format.lower(),
                            include_predictions=include_predictions
                        )
                        
                        st.success(f"Annotations exported successfully!")
                        st.markdown(f"📥 [Download Export]({export_file})")
                        
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")

if __name__ == "__main__":
    app = StreamlitSACAT()
    app.main()


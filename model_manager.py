import spacy
from spacy.tokens import DocBin
from spacy.tokens import Span, SpanGroup
import os
from pathlib import Path
from datetime import datetime
import logging
import shutil

class ModelManager:
    def __init__(self, project_path, gpu=False):
        """Initialize ModelManager
        
        Args:
            project_path (str): Path to project directory
            gpu (bool): Whether to use GPU for training
        
        Raises:
            ValueError: If project path doesn't exist
        """
        if not os.path.exists(project_path):
            raise ValueError(f"Project path {project_path} does not exist")
            
        self.project_path = project_path
        self.models_path = os.path.join(project_path, "models")
        os.makedirs(self.models_path, exist_ok=True)
        self.gpu = gpu
        self.current_model = None
        
        # Setup logging
        logging.basicConfig(
            filename=os.path.join(project_path, 'static', 'logs'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def create_training_data(self, sentences, annotations):
        """Convert annotations to spaCy training format
        
        Args:
            sentences (list): List of sentences
            annotations (list): List of annotations for each sentence
            
        Returns:
            DocBin: SpaCy DocBin object containing training data
            
        Raises:
            ValueError: If input data is invalid
        """
        if not sentences or not annotations:
            raise ValueError("Both sentences and annotations must be provided")
        if len(sentences) != len(annotations):
            raise ValueError("Number of sentences must match number of annotations")
            
        self.logger.info(f"Creating training data from {len(sentences)} sentences")
        
        nlp = spacy.blank("en")
        db = DocBin()
        
        for sentence, sent_annotations in zip(sentences, annotations):
            doc = nlp(sentence)
            spans = []
            for ann in sent_annotations:
                try:
                    span = doc.char_span(
                        ann['begin_idx'], 
                        ann['end_idx'],
                        label=str(ann['concept_id']),
                        alignment_mode="expand"
                    )
                    if span:
                        spans.append(span)
                except KeyError as e:
                    self.logger.error(f"Missing required key in annotation: {e}")
                    continue
            
            spangroup = SpanGroup(doc, name="sc", spans=spans)
            doc.spans["sc"] = spangroup
            db.add(doc)
        
        self.logger.info("Training data creation completed")
        return db
    
    def train_model(self, training_data, model_name):
        """Train a new model
        
        Args:
            training_data (DocBin): SpaCy DocBin containing training data
            model_name (str): Name for the new model
            
        Returns:
            str: Path to trained model
            
        Raises:
            ValueError: If training data is invalid
        """
        self.logger.info(f"Starting training for model: {model_name}")
        
        model_path = os.path.join(self.models_path, model_name)
        os.makedirs(model_path, exist_ok=True)
        
        # Save training data
        training_data.to_disk(os.path.join(model_path, "training.spacy"))
        
        # Enhanced training configuration
        config = {
            "paths": {
                "train": str(os.path.join(model_path, "training.spacy")),
                "dev": str(os.path.join(model_path, "training.spacy"))
            },
            "system": {
                "gpu_allocator": "pytorch" if self.gpu else None,
                "batch_size": 1000 if self.gpu else 100
            },
            "corpora": {
                "train": {"path": str(os.path.join(model_path, "training.spacy"))},
                "dev": {"path": str(os.path.join(model_path, "training.spacy"))}
            },
            "training": {
                "epochs": 20,
                "dropout": 0.2,
                "patience": 5,  # Early stopping
                "min_loss_decrease": 0.001
            }
        }
        
        try:
            # Initialize model
            nlp = spacy.blank("en")
            spancat = nlp.add_pipe("spancat", config={"spans_key": "sc"})
            
            # Train model
            optimizer = nlp.initialize(lambda: [])
            self.logger.info("Starting training iterations")
            
            for i in range(20):  # Number of iterations
                losses = {}
                nlp.update([next(training_data)], sgd=optimizer, losses=losses)
                self.logger.info(f"Iteration {i+1}/20 - Loss: {losses}")
            
            # Save model
            nlp.to_disk(os.path.join(model_path, "model"))
            self.current_model = nlp
            
            self.logger.info(f"Model training completed and saved to {model_path}")
            return model_path
            
        except Exception as e:
            self.logger.error(f"Error during model training: {str(e)}")
            if os.path.exists(model_path):
                shutil.rmtree(model_path)
            raise
    
    def load_model(self, model_name):
        """Load an existing model
        
        Args:
            model_name (str): Name of model to load
            
        Returns:
            spacy.language.Language: Loaded SpaCy model
            
        Raises:
            ValueError: If model doesn't exist
        """
        model_path = os.path.join(self.models_path, model_name, "model")
        if not os.path.exists(model_path):
            raise ValueError(f"Model {model_name} does not exist")
        
        try:
            self.logger.info(f"Loading model from {model_path}")
            self.current_model = spacy.load(model_path)
            return self.current_model
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            raise
    
    def predict(self, text):
        """Make predictions on new text
        
        Args:
            text (str): Text to make predictions on
            
        Returns:
            list: List of predictions with concept IDs and positions
            
        Raises:
            ValueError: If no model is loaded
        """
        if self.current_model is None:
            raise ValueError("No model loaded")
        
        try:
            doc = self.current_model(text)
            predictions = []
            
            for span in doc.spans["sc"]:
                predictions.append({
                    'concept_id': int(span.label_),
                    'begin_idx': span.start_char,
                    'end_idx': span.end_char,
                    'score': span._.score if hasattr(span._, 'score') else None
                })
            
            return predictions
        except Exception as e:
            self.logger.error(f"Error during prediction: {str(e)}")
            raise
    
    def evaluate_model(self, test_data):
        """Evaluate model performance
        
        Args:
            test_data (list): List of (text, annotations) tuples
            
        Returns:
            dict: Dictionary containing evaluation metrics
        """
        if self.current_model is None:
            raise ValueError("No model loaded")
        
        results = {
            'precision': 0,
            'recall': 0,
            'f1': 0,
            'total_predictions': 0,
            'correct_predictions': 0
        }
        
        try:
            for text, true_annotations in test_data:
                predictions = self.predict(text)
                # Add evaluation logic here
                # This is a placeholder for actual metric calculation
                
            return results
        except Exception as e:
            self.logger.error(f"Error during model evaluation: {str(e)}")
            raise
    
    def get_model_info(self, model_name):
        """Get information about a specific model
        
        Args:
            model_name (str): Name of the model
            
        Returns:
            dict: Dictionary containing model information
        """
        model_path = os.path.join(self.models_path, model_name)
        if not os.path.exists(model_path):
            raise ValueError(f"Model {model_name} does not exist")
        
        try:
            return {
                'name': model_name,
                'path': model_path,
                'created': datetime.fromtimestamp(os.path.getctime(model_path)),
                'size': sum(os.path.getsize(os.path.join(model_path, f)) 
                          for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f))),
                'last_modified': datetime.fromtimestamp(os.path.getmtime(model_path))
            }
        except Exception as e:
            self.logger.error(f"Error getting model info: {str(e)}")
            raise
    
    def get_available_models(self):
        """Get list of available models
        
        Returns:
            list: List of model names
        """
        try:
            return [d for d in os.listdir(self.models_path) 
                   if os.path.isdir(os.path.join(self.models_path, d))]
        except Exception as e:
            self.logger.error(f"Error getting available models: {str(e)}")
            raise
    
    def cleanup(self):
        """Cleanup method to free resources"""
        self.current_model = None
        self.logger.info("Model manager cleanup completed")

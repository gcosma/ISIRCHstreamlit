# model_manager.py

import spacy
from spacy.tokens import DocBin
from spacy.tokens import Span, SpanGroup
import os
from pathlib import Path

class ModelManager:
    def __init__(self, project_path, gpu=False):
        self.project_path = project_path
        self.models_path = os.path.join(project_path, "models")
        self.gpu = gpu
        self.current_model = None
        
    def create_training_data(self, sentences, annotations):
        """Convert annotations to spaCy training format"""
        nlp = spacy.blank("en")
        db = DocBin()
        
        for sentence, sent_annotations in zip(sentences, annotations):
            doc = nlp(sentence)
            spans = []
            for ann in sent_annotations:
                span = doc.char_span(
                    ann['begin_idx'], 
                    ann['end_idx'],
                    label=str(ann['concept_id']),
                    alignment_mode="expand"
                )
                if span:
                    spans.append(span)
            
            spangroup = SpanGroup(doc, name="sc", spans=spans)
            doc.spans["sc"] = spangroup
            db.add(doc)
        
        return db
    
    def train_model(self, training_data, model_name):
        """Train a new model"""
        model_path = os.path.join(self.models_path, model_name)
        os.makedirs(model_path, exist_ok=True)
        
        # Save training data
        training_data.to_disk(os.path.join(model_path, "training.spacy"))
        
        # Configure training
        config = {
            "paths": {
                "train": str(os.path.join(model_path, "training.spacy")),
                "dev": str(os.path.join(model_path, "training.spacy"))
            },
            "system": {"gpu_allocator": "pytorch" if self.gpu else None},
            "corpora": {"train": {"path": str(os.path.join(model_path, "training.spacy"))}}
        }
        
        # Initialize model
        nlp = spacy.blank("en")
        spancat = nlp.add_pipe("spancat", config={"spans_key": "sc"})
        
        # Train model
        optimizer = nlp.initialize(lambda: [])
        for _ in range(20):  # Number of iterations
            losses = {}
            nlp.update([next(training_data)], sgd=optimizer, losses=losses)
        
        # Save model
        nlp.to_disk(os.path.join(model_path, "model"))
        self.current_model = nlp
        
        return model_path
    
    def load_model(self, model_name):
        """Load an existing model"""
        model_path = os.path.join(self.models_path, model_name, "model")
        if not os.path.exists(model_path):
            raise ValueError(f"Model {model_name} does not exist")
        
        self.current_model = spacy.load(model_path)
        return self.current_model
    
    def predict(self, text):
        """Make predictions on new text"""
        if self.current_model is None:
            raise ValueError("No model loaded")
        
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
    
    def get_available_models(self):
        """Get list of available models"""
        return [d for d in os.listdir(self.models_path) 
                if os.path.isdir(os.path.join(self.models_path, d))]

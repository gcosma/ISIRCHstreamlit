import spacy
from spacy.tokens import DocBin, SpanGroup
from pathlib import Path
import shutil
import os

class SpacyModel:
    """
    Handles spaCy model operations including training and prediction.
    Supports both CPU and GPU configurations.
    """
    def __init__(self, project, model_id=None, gpu=False):
        """
        Initialize spaCy model
        
        Args:
            project: AnnotationProject instance
            model_id: Optional model ID to load existing model
            gpu: Whether to use GPU acceleration
        """
        self.project = project
        self.gpu = gpu
        self.model = None
        
        # Set model ID
        if model_id is None:
            existing_models = [int(x) for x in os.listdir(self.project.project_path / "models") 
                             if x.isdigit()]
            self.model_id = max(existing_models) + 1 if existing_models else 1
        else:
            self.model_id = model_id
            
        # Create model directory
        self.model_path = self.project.project_path / "models" / str(self.model_id)
        os.makedirs(self.model_path, exist_ok=True)
        
        # Copy appropriate config
        config_name = "base_config_spancat_gpu.cfg" if gpu else "base_config_spancat_cpu.cfg"
        if not os.path.exists(self.model_path / "config.cfg"):
            shutil.copy(
                Path("static/config") / config_name,
                self.model_path / "config.cfg"
            )

    def build_model(self):
        """Build and initialize the spaCy model"""
        if not os.path.exists(self.model_path / "model-best"):
            # Create new model
            self.model = spacy.blank("en")
            
            # Prepare training data
            db = DocBin()
            annotations = self.project.export_annotations()
            
            for text, spans in annotations:
                doc = self.model(text)
                doc_spans = []
                for start, end, label in spans:
                    span = doc.char_span(start, end, label=label, alignment_mode="expand")
                    if span:
                        doc_spans.append(span)
                
                spangroup = SpanGroup(doc, name="sc", spans=doc_spans)
                doc.spans["sc"] = spangroup
                db.add(doc)
            
            # Save training data
            db.to_disk(self.model_path / "train.spacy")
            db.to_disk(self.model_path / "dev.spacy")
        else:
            # Load existing model
            self.model = spacy.load(self.model_path / "model-best")
        
        return self.model_id

    def train(self):
        """Train the spaCy model"""
        from spacy.cli.train import train as spacy_train
        
        config_path = self.model_path / "config.cfg"
        output_path = self.model_path / "trained"
        
        # Training arguments
        overrides = {
            "paths.train": str(self.model_path / "train.spacy"),
            "paths.dev": str(self.model_path / "dev.spacy")
        }
        
        # Train model
        if self.gpu:
            spacy_train(config_path, output_path, overrides=overrides, use_gpu=0)
        else:
            spacy_train(config_path, output_path, overrides=overrides)
        
        # Load trained model
        self.model = spacy.load(output_path / "model-best")

    def predict(self, text):
        """
        Make predictions on a single text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of (concept_id, start_idx, end_idx) tuples
        """
        if not self.model:
            raise ValueError("Model not initialized. Call build_model() first.")
        
        doc = self.model(text)
        predictions = []
        
        for span in doc.spans["sc"]:
            predictions.append([
                int(span.label_),
                span.start_char,
                span.end_char
            ])
        
        return predictions

    def predict_all(self):
        """Predict annotations for all sentences in the project"""
        results = []
        for sentence_id, sentence in self.project.get_all_sentences():
            predictions = self.predict(sentence)
            for concept_id, start_idx, end_idx in predictions:
                self.project.set_annotations(
                    sentence_id=sentence_id,
                    concept_id=concept_id,
                    begin_idx=start_idx,
                    end_idx=end_idx,
                    model_id=self.model_id,
                    predict=True,
                    accept_reject_not=2  # Not reviewed
                )
            results.append([sentence_id, predictions])
        return results

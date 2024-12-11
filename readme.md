# Streamlit Concept Annotation Tool

A web-based tool for annotating text with concepts, built with Streamlit and Spacy.

## Features

- Create and manage annotation projects
- Add and organize concepts with color coding
- Annotate text with multiple concepts
- Integration with Spacy for model-based predictions
- SQLite database for persistent storage

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/annotation-tool.git
cd annotation-tool
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Streamlit application:
```bash
streamlit run src/app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (usually http://localhost:8501)

3. Create a new project or load an existing one

4. Add concepts and begin annotating your texts

## Project Structure

```
annotation-tool/
├── src/              # Source code
├── tests/            # Test files
├── docs/             # Documentation
└── requirements.txt  # Python dependencies
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Your Name - your.email@example.com
Project Link: https://github.com/yourusername/annotation-tool

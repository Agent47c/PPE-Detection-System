# 🤝 Contributing to PPE Safety Monitor

First off, thank you for considering contributing to PPE Safety Monitor! It's people like you that make this tool better for workplace safety worldwide.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Bug Reports](#bug-reports)
- [Feature Requests](#feature-requests)

---

## 📜 Code of Conduct

- **Be respectful** of differing viewpoints and experiences
- **Accept constructive criticism** gracefully
- **Focus on what's best** for the community and workplace safety
- **Show empathy** towards other community members

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- Basic understanding of computer vision/ML concepts
- Familiarity with PyQt5 (for UI contributions)

### Quick Start
```bash
# Fork and clone
git clone https://github.com/your-username/ppe-safety-monitor.git
cd ppe-safety-monitor

# Create branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Add: Brief description of changes"

# Push and create PR
git push origin feature/your-feature-name
```

---

## 💻 Development Setup

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Additional dev tools
```

### 2. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or your preferred editor
```

### 3. Pre-commit Hooks (Recommended)
```bash
pip install pre-commit
pre-commit install
```

---

## 🛠️ How to Contribute

### Types of Contributions

#### 🐛 Bug Fixes
- Check [existing issues](https://github.com/yourusername/ppe-safety-monitor/issues)
- Create a new issue if not reported
- Reference issue number in PR

#### ✨ New Features
- Discuss in [Discussions](https://github.com/yourusername/ppe-safety-monitor/discussions) first
- Create feature request issue
- Get approval before major changes

#### 📚 Documentation
- Improve README, guides, or code comments
- Add examples or tutorials
- Fix typos or unclear sections

#### 🎨 UI/UX Improvements
- Enhance visual design
- Improve user experience
- Add accessibility features

#### 🧪 Testing
- Add unit tests
- Improve test coverage
- Add integration tests

---

## 📝 Coding Standards

### Python Style Guide
Follow [PEP 8](https://pep8.org/) with these specifics:

```python
# Imports: stdlib, third-party, local
import os
import sys

import cv2
import numpy as np

from objecttracking import YOLODetector
from auth_manager import AuthManager

# Class names: PascalCase
class ViolationDetector:
    pass

# Functions/variables: snake_case
def process_frame(frame_data):
    detection_result = detect_objects(frame_data)
    return detection_result

# Constants: UPPER_SNAKE_CASE
MAX_BUFFER_SIZE = 100
DEFAULT_CONFIDENCE = 0.35

# Private methods: _leading_underscore
def _internal_helper(data):
    pass
```

### Code Structure
```python
# Module docstring
"""
Module for handling PPE violation detection.

This module provides real-time violation monitoring
and alert generation capabilities.
"""

# Imports

# Constants

# Classes
class MyClass:
    """Class docstring with description."""
    
    def __init__(self):
        """Initialize the class."""
        pass
    
    def public_method(self):
        """
        Public method with docstring.
        
        Args:
            param1: Description
            
        Returns:
            Description of return value
        """
        pass
    
    def _private_method(self):
        """Private method for internal use."""
        pass

# Functions

# Main execution
if __name__ == "__main__":
    pass
```

### Documentation
```python
def complex_function(param1, param2, optional_param=None):
    """
    Brief one-line description.
    
    Longer description explaining the function's purpose,
    behavior, and any important details.
    
    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2
        optional_param (bool, optional): Description. Defaults to None.
    
    Returns:
        dict: Description of return value with structure:
            {
                'key1': value_description,
                'key2': value_description
            }
    
    Raises:
        ValueError: When param1 is invalid
        RuntimeError: When operation fails
    
    Example:
        >>> result = complex_function("test", 42)
        >>> print(result['key1'])
        'value'
    """
    pass
```

---

## 🧪 Testing Guidelines

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_detection.py

# Run specific test
pytest tests/test_detection.py::test_yolo_detection
```

### Writing Tests
```python
import pytest
from objecttracking import YOLODetector

class TestYOLODetector:
    """Test suite for YOLODetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance for testing."""
        return YOLODetector("model.pt")
    
    def test_initialization(self, detector):
        """Test detector initializes correctly."""
        assert detector is not None
        assert detector.confidence == 0.35
    
    def test_prediction(self, detector, sample_frame):
        """Test prediction returns valid results."""
        results = detector.predict(sample_frame)
        assert results is not None
        assert len(results) > 0
```

### Test Coverage
- Aim for **>80% code coverage**
- Test edge cases and error conditions
- Include integration tests for critical workflows

---

## 🔄 Pull Request Process

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass locally
- [ ] No merge conflicts

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
Describe testing performed

## Screenshots (if UI changes)
Add screenshots here

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed
- [ ] Commented complex logic
- [ ] Updated documentation
- [ ] Added tests
- [ ] Tests pass
```

### Review Process
1. Submit PR with clear description
2. Wait for automated checks
3. Address reviewer feedback
4. Maintainer approves and merges

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format
<type>(<scope>): <subject>

# Types
feat:     New feature
fix:      Bug fix
docs:     Documentation
style:    Formatting
refactor: Code restructuring
test:     Adding tests
chore:    Maintenance

# Examples
feat(detection): Add confidence threshold adjustment
fix(alerts): Resolve SMTP connection timeout
docs(readme): Update installation instructions
test(tracking): Add unit tests for ObjectTracker
```

---

## 🐛 Bug Reports

### Before Reporting
1. Check [existing issues](https://github.com/yourusername/ppe-safety-monitor/issues)
2. Update to latest version
3. Search [Discussions](https://github.com/yourusername/ppe-safety-monitor/discussions)

### Bug Report Template
```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen

**Screenshots**
Add screenshots if applicable

**Environment:**
- OS: [e.g., Windows 10]
- Python version: [e.g., 3.10]
- GPU: [e.g., NVIDIA RTX 3060]
- CUDA version: [e.g., 11.8]

**Additional context**
Any other relevant information
```

---

## 💡 Feature Requests

### Before Requesting
1. Check if already requested
2. Consider if it aligns with project goals
3. Think about implementation complexity

### Feature Request Template
```markdown
**Is your feature related to a problem?**
Clear description of the problem

**Describe the solution**
How should this feature work?

**Describe alternatives**
Other solutions you've considered

**Additional context**
Mockups, examples, or references

**Implementation considerations**
Technical challenges or requirements
```

---

## 🏗️ Project Architecture

### Component Overview
```
app.py                 → Main application & UI
├── MainWindow         → Window manager
├── MonitorScreen      → Detection/tracking UI
├── ViolationScreen    → Violation monitoring UI
├── ConnectionScreen   → Camera connection
└── VideoThread        → Background processing

objecttracking.py      → Computer vision backend
├── VideoLoader        → Frame capture
├── YOLODetector       → Object detection
├── ObjectTracker      → Multi-object tracking
├── ViolationDetector  → Violation logic
└── Main_App           → Backend coordinator

auth_manager.py        → Supabase authentication
```

### Adding New Features

#### UI Components
```python
# In app.py
class MyNewScreen(BaseMonitorScreen):
    def __init__(self):
        super().__init__(screen_type="custom")
        self.create_main_layout()
    
    def create_control_buttons(self):
        # Add your buttons
        pass
```

#### Backend Components
```python
# In objecttracking.py
class MyNewDetector:
    def __init__(self, model_path):
        self.model = load_model(model_path)
    
    def detect(self, frame):
        # Detection logic
        return results
```

---

## 📊 Performance Optimization

### Guidelines
- Profile before optimizing: `python -m cProfile app.py`
- Use numpy vectorization over loops
- Implement frame skipping for non-critical tasks
- Cache expensive computations
- Use threading for I/O operations

### Example
```python
# ❌ Slow
for box in detection_boxes:
    processed = process_box(box)
    results.append(processed)

# ✅ Fast
import numpy as np
results = np.vectorize(process_box)(detection_boxes)
```

---

## 🔐 Security Considerations

### Important Rules
- **Never commit** `.env` files or credentials
- **Never hardcode** API keys or passwords
- **Always validate** user input
- **Use parameterized** queries (SQL injection)
- **Sanitize file paths** (path traversal)
- **Implement rate limiting** for API endpoints

### Example
```python
# ❌ Bad
password = "hardcoded_password"
query = f"SELECT * FROM users WHERE email='{email}'"

# ✅ Good
password = os.getenv("PASSWORD")
query = "SELECT * FROM users WHERE email=?"
cursor.execute(query, (email,))
```

---

## 📞 Getting Help

- 💬 [GitHub Discussions](https://github.com/yourusername/ppe-safety-monitor/discussions) - Questions and ideas
- 🐛 [GitHub Issues](https://github.com/yourusername/ppe-safety-monitor/issues) - Bug reports
- 📧 Email: dev@your-domain.com
- 💼 [Discord Community](https://discord.gg/your-server) (if available)

---

## 🎉 Recognition

Contributors will be recognized in:
- README.md Contributors section
- Release notes
- Project documentation

Thank you for making workplace safety better! 🛡️

---

<div align="center">

**Questions? Open a [Discussion](https://github.com/yourusername/ppe-safety-monitor/discussions)!**

</div>
# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# First upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Run the app

python app.py
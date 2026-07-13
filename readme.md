
# 1. Create the virtual environment
python3 -m venv venv

# set up an internally manage enviornment for safety
source venv/bin/activate  
# on windows 
venv\Scripts\activate

# 3. Install requirements
pip install -r requirements.txt

<h3>How to run the script </h3>

# Without images (default)
python printready.py https://en.wikipedia.org/wiki/Toilet_paper_orientation

# With greyscale images
python printready.py https://en.wikipedia.org/wiki/Toilet_paper_orientation --images
# Ignore any warnings about RGBA transparency, this is designed to save your ink. 


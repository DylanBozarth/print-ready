
# set up an internally manage enviornment for safety
source venv/bin/activate


# Install requirements 
pip -install -r requirements.txt 


# Without images (default)
python printready.py https://en.wikipedia.org/wiki/House_of_Aviz

# With greyscale images
python printready.py https://en.wikipedia.org/wiki/House_of_Aviz --images


https://higheredintel.substack.com/p/online-growth-nslds-changes-and-research
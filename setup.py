import os

# Install pipenv
if os.system("pip3 install pipenv") and os.system("pip install pipenv"):
    print("Couldn't locate neither pip nor pip3 commands, please install pip")

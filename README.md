# Welcome to the Patient-to-Room Instance Generator

## Installation
The project is written in *Python* and uses a *Django* web server.
This version of the instance generator currently does not work on Windows, and we recommend using a Mac or Linux operating system.
You need to install all required python packages.
It is recommended to use a virtual environment for that.
Follow the steps:
1. Install a current python version, if it is not already the case (*python3* is pre-installed on MacOS and many Linux distributions).
1. Using the terminal, enter the directory of the project.
1. Create a virtual environment, for example using *venv*, by running `python3 -m venv .venv`. This creates a virtual environment in a *.venv* folder.
1. Activate the virtual environment via `source .venv/bin/activate`. In case you want to leave the virtual environment after using the project, you can type in `deactivate`.
1. Now, install all requirements (within the virtual environment): `pip install -r website/requirements.txt`
2. If it is the first time, execute `python website/manage.py migrate` to ensure that the data base functions properly.
1. Start the *Django* server by `python website/manage.py runserver`. This may take a while doing it the first time.
1. You can now reach the *Instance Generator* through a browser by opening `http://127.0.0.1:8000/`.

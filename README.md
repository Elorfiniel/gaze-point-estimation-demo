# Gaze Point Estimation (Demo)

A Processing Demo for the Application of PoG Estimation. Model Trained using this Codebase: [gaze-point-estimation-2023](https://gitee.com/elorfiniel/gaze-point-estimation-2023).

| Intro | Game | Outro |
| -------------- | -------------- | -------------- |
| ![intro](gallery/intro.png) | ![game](gallery/game.png) | ![outro](gallery/outro.png) |

## Setup

The demo consists of a Python backend (server) and a JavaScript frontend (client) that exchange data using the WebSocket API. To run the demo, please follow these steps:

1. Install the requirements for the Python backend.
2. Start the python backend (`estimator/estimator.py`).
3. Visit the hosted demo webpage (`sketch/demo.html`).

The following cheatsheet demonstrates how you can setup and run this demo from the command line. Alternatively, you can serve the demo webpage on your own (for instance, using the [Live Server Extension](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) in Visual Studio Code).

### Install Dependencies

```shell
# create a python virtual environment for dependencies
python -m venv --upgrade-deps venv

# activate the virtual environment
venv/Scripts/activate.bat # (windows: cmd)
venv/Scripts/Activate.ps1 # (windows: pwsh)
source venv/bin/activate  # (linux / mac)

# install required dependencies using pip
pip install -r estimator/requirements.txt
```

Now, you'll have the environment properly setup.

### Run the Demo

```shell
# start the python backend (server)
cd estimator
python estimator.py

# start the javascript frontend (client)
cd sketch
python -m http.server --bind 127.0.0.1 5500
```

Now, open the browser and visit [the demo page](http://127.0.0.1:5500/demo.html) served on `localhost:5500`.

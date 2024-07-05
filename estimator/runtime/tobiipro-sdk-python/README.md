# Instructions on the Setup of Tobii Pro SDK

1. Download the Tobii Pro SDK (Python), via the following URL.

    https://connect.tobii.com/s/sdk-downloads?language=en_US

2. Extract the corresponding files for your platform to this folder.

    ```shell
    tobiipro-sdk-python/
     |- README.md
     |- tobiiresearch/
     |- tobii_research.py
    ```

3. Add this folder to your PYTHONPATH environment variable.

    ```shell
    export PYTHONPATH=$PYTHONPATH:/path/to/tobiipro-sdk-python  # (linux / mac)
    $ENV:PYTHONPATH = /path/to/tobiipro-sdk-python              # (windows: pwsh)
    ```

    Additionally, if you are using a virtual environment, you may mannually configure the activate script for the virtual environment.

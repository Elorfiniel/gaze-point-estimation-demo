# Instructions on the Setup of Tobii Pro SDK

## Marked as Deprecated (2024-07-05)

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

## Furthur Reading

**[Note]** Tobii Pro SDK (Python) may contain a corrupted dynamic library, see also: [import error tobii_research_interop](https://developer.tobii.com/community/forums/topic/import-error-tobii_research_interop/).

An alternative is to use [Titta](https://pypi.org/project/titta/).

This project includes the `tobiipro-sdk-c` folder, which contains the C implementation for the Tobii Pro SDK. You can download the SDK from the same URL as where the Python SDK is downloaded. Unzip and copy the `include` and `lib` folders to the `tobiipro-sdk-c/3rd-party` folder.`

If time permits, this project will build its own bindings/wrappers for the Tobii Pro SDK (C).

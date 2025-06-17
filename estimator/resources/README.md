# External Resources

This project makes use of external resources from several popular projects. Despite optional, these resources are required for full functionality, such as the annotation tool `annotator.py`. If you are not using any of the optional features, you can safely ignore this section.

## Annotation Tool

The annotation tool features a `FaceEmbeddingPass` that uses [the model](https://github.com/timesler/facenet-pytorch/releases/download/v2.2.9/20180402-114759-vggface2.pt) from [FaceNet-PyTorch](https://github.com/timesler/facenet-pytorch?tab=readme-ov-file) to extract embeddings for all recorded faces. The extracted embeddings are used to calculate the similarity between faces, so as to filter out samples that do not match the recorded person. Please follow these instructions to convert the model to ONNX format:

```shell
# create a new virtual environment
python -m venv --upgrade-deps facenet

# activate the virtual environment
facenet/Scripts/activate.bat # (windows: cmd)
facenet/Scripts/Activate.ps1 # (windows: pwsh)
source facenet/bin/activate  # (linux / mac)

# install required dependencies using pip
pip install facenet-pytorch onnxruntime==1.15.1

# convert the model to onnx format
python facenet.py
```

If everything goes well, you should see a `facenet.onnx` file produced in the this folder, i.e. `resources/facenet.onnx`. You can now deactivate and remove the temporary virtual environment `facenet`, as well as the cached model in `TORCH_HOME`.

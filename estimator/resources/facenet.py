from facenet_pytorch import InceptionResnetV1

import numpy as np
import torch
import onnxruntime


model = InceptionResnetV1(pretrained='vggface2').eval().cpu()
example_input = (torch.rand(1, 3, 160, 160) - 0.5) / 0.5

torch.onnx.export(
  model, example_input, 'facenet.onnx', export_params=True,
  opset_version=14, output_names=['emb'], input_names=['img'],
)


with torch.no_grad():
  opt_ref = model(example_input)

ort_session = onnxruntime.InferenceSession('facenet.onnx')
opt_cvt = ort_session.run(None, {'img': example_input.numpy()})

np.testing.assert_almost_equal(opt_ref.numpy(), opt_cvt[0])

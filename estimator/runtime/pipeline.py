import cv2  # OpenCV-Python
import numpy as np
import onnx, onnxruntime
import os.path as osp


def load_onnx_model(model_path):
  model_path = osp.abspath(model_path)

  model = onnx.load_model(model_path)
  onnx.checker.check_model(model)
  model = onnxruntime.InferenceSession(model_path)

  return model

def load_model(config_path, model_path):
  config_root = osp.dirname(osp.abspath(config_path))
  model_path = osp.join(config_root, model_path)
  return load_onnx_model(model_path)


def prepare_input_image_crop(cv2_image):
  np_image = np.array(cv2_image, dtype=np.float32) / 255.0

  mean = np.array([0.485, 0.456, 0.406])
  std = np.array([0.229, 0.224, 0.225])
  normed_image = (np_image - mean) / std

  np_image = np.transpose(normed_image, axes=(2, 0, 1))

  np_image = np_image.astype(dtype=np.float32)
  np_image = np.expand_dims(np_image, axis=0)

  return np_image

def prepare_input_key_points(face_bbox, eye_ldmks):
  kpts_ip = np.concatenate([face_bbox, eye_ldmks], axis=0)

  kpts_ip = kpts_ip.astype(dtype=np.float32)
  kpts_ip = np.expand_dims(kpts_ip, axis=0)

  return kpts_ip

def prepare_model_input(face_crop, reye_crop, leye_crop, eye_ldmks,
                        face_resize=(224, 224), eyes_resize=(224, 224)):
  # Get resized crops: ndarray of shape (h, w, c)
  face = cv2.resize(face_crop.get_crop(), face_resize, interpolation=cv2.INTER_CUBIC)
  reye = cv2.resize(reye_crop.get_crop(), eyes_resize, interpolation=cv2.INTER_CUBIC)
  leye = cv2.resize(leye_crop.get_crop(), eyes_resize, interpolation=cv2.INTER_CUBIC)

  # Convert inputs to ndarrays requested by the estimation model
  model_input = {
    'face': prepare_input_image_crop(face),
    'reye': prepare_input_image_crop(reye),
    'leye': prepare_input_image_crop(leye),
    'kpts': prepare_input_key_points(face_crop.get_sas(), eye_ldmks),
  }

  return model_input


def rotate_vector_a(x, y, theta):
  theta = np.deg2rad(theta)
  cos, sin = np.cos(theta), np.sin(theta)

  M = np.array([
    [cos, -sin],
    [sin, cos]
  ], dtype=np.float32)
  v = np.array([x, y], dtype=np.float32)

  return np.transpose(np.dot(M, np.transpose(v)))

def rotate_vector_v(x, y, theta):
  theta = np.deg2rad(theta)
  cos, sin = np.cos(theta), np.sin(theta)

  M = np.array([
    [cos, -sin],
    [sin, cos],
  ], dtype=np.float32)
  v = np.array([x, y], dtype=np.float32)

  return np.stack([
    np.transpose(np.dot(M[:, :, i], np.transpose(v[:, i])))
    for i in range(len(theta))
  ], axis=0)

def do_model_inference(model, model_input):
  return model.run(None, model_input)

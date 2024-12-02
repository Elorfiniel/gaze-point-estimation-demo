import numpy as np


class FaceAlignment():
  '''Wrapper class for mediapipe face mesh solution.'''

  def __init__(self,
               static_image_mode=True,
               max_num_faces=1,
               min_detection_confidence=0.6,
               min_tracking_confidence=0.6):
    '''Helper class for mediapipe face mesh solution with context management.

    Similar to mediapipe solutions, we recommand the use of `with` block:

    ```
    with FaceAlignment(min_detection_confidence=0.8) as alignment:
      image_path = generate_image_path(...)
      image = load_and_convert_to_rgb(image_path)
      landmarks, theta = alignment.process(image)
      if len(landmarks) == 0: continue
      crops, norm_ldmks, new_ldmks = alignment.get_face_crop(image, landmarks, theta)
    ```

    `static_image_mode`: treat the input as stand-alone images or frames from a video stream.

    `max_num_faces`: maximum number of faces to detect.

    `min_detection_confidence`: minimum confidence value (0.0, 1.0) for successful face detection.

    `min_tracking_confidence`: minimum confidence value (0.0, 1.0) for successful face landmarks tracking.
    '''

    self._static_image_mode = static_image_mode
    self._max_num_faces = max_num_faces
    self._min_detection_confidence = min_detection_confidence
    self._min_tracking_confidence = min_tracking_confidence

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    pass

  def get_rotation_matrix_2d(self, center=(0.0, 0.0), theta=0.0, scale=1.0):
    raise NotImplementedError(f'for full functionality, please install mediapipe ...')

  def apply_rotation_matrix_2d(self, M: np.ndarray, points: np.ndarray):
    raise NotImplementedError(f'for full functionality, please install mediapipe ...')

  def process(self, image: np.ndarray):
    raise NotImplementedError(f'for full functionality, please install mediapipe ...')

  def close(self):
    raise NotImplementedError(f'for full functionality, please install mediapipe ...')

  def get_face_crop_without_align(self, image, landmarks, with_eyes=True,
                                  width_expand=1.6, hw_ratio=0.6):
    raise NotImplementedError(f'for full functionality, please install mediapipe ...')

  def get_face_crop(self, image, landmarks, theta, with_eyes=True,
                    width_expand=1.6, hw_ratio=0.6):
    raise NotImplementedError(f'for full functionality, please install mediapipe ...')

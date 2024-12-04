from .miscellaneous import use_state

import cv2


class VideoCaptureBuilder:
  def __init__(self, capture_id, resolution=None):
    '''Build cv2.VideoCapture with the given capture_id and resolution.

    `capture_id`: index, filename, image sequence or url, see also cv2.VideoCapture.

    `resolution`: resolution (h, w) to set for the video capture.
    '''

    self.capture_id = capture_id
    self.resolution = resolution

  def build(self):
    capture = cv2.VideoCapture(self.capture_id, cv2.CAP_ANY)

    if self.resolution is not None:
      capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[0])
      capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[1])

    return capture


class CaptureHandler:
  def __init__(self, capture_builder, frame_consumer):
    '''CaptureHandler maintains a cv2.VideoCapture and calls the given
    frame consumer for each frame captured, until the exit flag is set.

    `capture_builder`: capture builder that implements a `build` method.

    `frame_consumer`: a callable that takes the captured frame and the
    callback function that sets the exit condition.
    '''

    self.capture_builder = capture_builder
    self.frame_consumer = frame_consumer

  def main_loop(self, **extra_kwargs):
    capture = self.capture_builder.build()
    exit_cond, set_exit_cond = use_state(False)

    while not exit_cond():
      success, src_image = capture.read()
      if not success: continue
      self.frame_consumer(src_image, set_exit_cond, **extra_kwargs)

    capture.release()

import cv2  # OpenCV-Python
import datetime
import logging
import os


class FrameCache():
  def __init__(self, max_count: 600):
    '''A simple FIFO cache with limited max size.'''

    self.frame_count = 0
    self.max_count = max_count
    self.frame_cache = []
    self.tid_cache = []

  def insert_frame(self, frame, tid):
    if self.frame_count >= self.max_count:
      self.frame_cache.pop(0)
      self.tid_cache.pop(0)
      self.frame_count -= 1

    self.frame_cache.append(frame)
    self.tid_cache.append(tid)
    self.frame_count += 1

  def fast_fetch(self, tid):
    fetched_item = None

    try:  # Find the frame tagged 'tid'
      item_idx = self.tid_cache.index(tid)
      fetched_item = self.frame_cache[item_idx]

      self.frame_cache = self.frame_cache[item_idx + 1:]
      self.tid_cache = self.tid_cache[item_idx + 1:]
      self.frame_count -= (item_idx + 1)

    except ValueError:
      self.frame_cache = []
      self.tid_cache = []
      self.frame_count = 0

    return fetched_item


class RecordingManager():
  def __init__(self, root: str):
    '''A simple recording manager based on time and item count.'''

    self.root = os.path.abspath(root)
    self.new_recording()

    try:
      os.makedirs(self.root, exist_ok=True)
    except Exception as ex:
      logging.warning(f'cannot make root directory "{self.root}", due to {ex}')

  def new_recording(self):
    self.folder = datetime.datetime.now().strftime('%m-%d-%Y-%H-%M-%S')
    self.item_count = 0

    folder_path = os.path.join(self.root, self.folder)

    try:
      os.makedirs(folder_path, exist_ok=True)
    except Exception as ex:
      logging.warning(f'cannot make recording folder "{folder_path}", due to {ex}')

  def save_frame(self, frame, px, py, lx, ly):
    item_label = f'{px:.4f}_{py:.4f}_{lx:.4f}_{ly:.4f}'
    frame_name = f'{self.item_count:05d} {item_label}.jpg'

    frame_path = os.path.join(self.root, self.folder, frame_name)

    try:  # Save frame to the specified path
      cv2.imwrite(frame_path, frame)
      self.item_count += 1
    except Exception as ex:
      logging.warning(f'cannot save frame to path "{frame_path}", due to {ex}')

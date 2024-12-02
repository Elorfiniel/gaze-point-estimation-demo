import cv2  # OpenCV-Python
import datetime
import logging
import os


class FrameCache():
  def __init__(self, max_count=600):
    '''A simple FIFO cache with limited max size.'''

    self.frame_count = 0
    self.max_count = max_count
    self.frame_cache = []
    self.fid_cache = []

  def insert_frame(self, frame, fid):
    if self.frame_count >= self.max_count:
      self.frame_cache.pop(0)
      self.fid_cache.pop(0)
      self.frame_count -= 1

    self.frame_cache.append(frame)
    self.fid_cache.append(fid)
    self.frame_count += 1

  def fast_fetch(self, fid):
    fetched_item = None

    try:  # Find the frame tagged 'fid'
      item_idx = self.fid_cache.index(fid)
      fetched_item = self.frame_cache[item_idx]

      self.frame_cache = self.frame_cache[item_idx + 1:]
      self.fid_cache = self.fid_cache[item_idx + 1:]
      self.frame_count -= (item_idx + 1)

    except ValueError:
      self.frame_cache = []
      self.fid_cache = []
      self.frame_count = 0

    return fetched_item


class RecordingManager():
  def __init__(self, root: str):
    '''A simple recording manager based on time and item count.'''

    self.root = os.path.abspath(root)

    try:
      os.makedirs(self.root, exist_ok=True)
      logging.info(f'recording root folder "{self.root}" created')
    except Exception as ex:
      logging.warning(f'cannot make root directory "{self.root}", due to {ex}')

  def new_recording(self, folder=''):
    self.folder = folder or datetime.datetime.now().strftime('%m-%d-%Y-%H-%M-%S')
    self.item_count = 0

    folder_path = os.path.join(self.root, self.folder)

    try:
      os.makedirs(folder_path, exist_ok=True)
    except Exception as ex:
      logging.warning(f'cannot make recording folder "{folder_path}", due to {ex}')

  def save_frame(self, frame, gx, gy, lx, ly, image_ext='.jpg'):
    item_label = f'{gx:.4f}_{gy:.4f}_{lx:.4f}_{ly:.4f}'
    frame_name = f'{self.item_count:05d} {item_label}.jpg'

    frame_path = os.path.join(self.root, self.folder, frame_name)

    try:  # Save frame to the specified path
      encoded, buffer = cv2.imencode(image_ext, frame)
      if encoded:
        buffer.tofile(frame_path)
        self.item_count += 1
    except Exception as ex:
      logging.warning(f'cannot save frame to path "{frame_path}", due to {ex}')

from .base_pass import BasePass

from runtime.es_config import EsConfig, EsConfigFns

import os
import os.path as osp
import shutil


class ReorganizeFolderPass(BasePass):

  PASS_NAME = 'mgmt_pass.reorganize_folder'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path

  def run(self, **kwargs):
    record_path, recording = osp.split(self.recording_path)

    # Create temporary folder for this recording
    temp_folder = osp.join(record_path, f'temp-{recording}')
    os.makedirs(temp_folder, exist_ok=True)

    # Create labels folder, then rename original label file
    labels_folder = osp.join(temp_folder, 'labels')
    os.makedirs(labels_folder, exist_ok=True)

    labels_src_path = osp.join(self.recording_path, 'labels.json')
    labels_dst_path = osp.join(labels_folder, 'targets.json')
    shutil.move(labels_src_path, labels_dst_path)

    # Create images folder by moving and renaming
    shutil.move(self.recording_path, temp_folder)
    images_src_folder = osp.join(temp_folder, recording)
    images_dst_folder = osp.join(temp_folder, 'images')
    os.rename(images_src_folder, images_dst_folder)

    # Make temporary folder the new recording folder
    os.rename(temp_folder, self.recording_path)

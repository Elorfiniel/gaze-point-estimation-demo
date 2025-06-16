from .base_pass import BasePass

from runtime.es_config import EsConfig

import json
import os.path as osp


class LoadLabelsPass(BasePass):

  PASS_NAME = 'io_pass.load_labels'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def run(self, context, **kwargs):
    json_path = osp.join(self.recording_path, 'labels.json')
    with open(json_path, 'r') as json_file:
      labels = json.load(json_file)
    context['labels'] = labels

import json
import os.path as osp


def _load_json(json_path):
  with open(json_path, 'r') as json_file:
    json_data = json.load(json_file)
  return json_data

def _dump_json(json_data, json_path):
  with open(json_path, 'w') as fp:
    json.dump(json_data, fp, indent=None)


class _TargetIterator:
  def __init__(self, labels):
    self.labels = labels

  def __iter__(self):
    self.index = 0
    return self

  def __next__(self):
    if self.index < len(self.labels):
      target = self.labels[self.index]
      self.index += 1
      return target
    else:
      raise StopIteration


class LabelPass:
  def action(self, target: dict):
    '''Process a single target, modify the target labels in place.'''
    pass

  def before_target_iter(self):
    '''Called before the first target is processed.'''
    pass

  def after_target_iter(self):
    '''Called after the last target is processed.'''
    pass

class LabelLoop:
  def __init__(self, record_path, recording):
    self.folder = osp.join(record_path, recording)

  def process(self, label_action: LabelPass):
    label_path = osp.join(self.folder, 'labels.json')
    label_data = _load_json(label_path)

    label_action.before_target_iter()
    for target in _TargetIterator(label_data):
      label_action.action(target)
    label_action.after_target_iter()

    _dump_json(label_data, label_path)

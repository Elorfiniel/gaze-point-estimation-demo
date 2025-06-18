from .base_pass import BasePass

import json
import os.path as osp


def require_context(bpass: BasePass, context: dict, item_names: list):
  for item_name in item_names:
    if context.get(item_name) is None:
      raise RuntimeError(f'{bpass.PASS_NAME} requires "{item_name}" in context')


def load_json(json_path: str, **kwargs):
  json_path = osp.abspath(json_path)

  with open(json_path, 'r') as json_file:
    json_data = json.load(json_file, **kwargs)
  return json_data


def dump_json(json_path: str, json_data: dict, **kwargs):
  json_path = osp.abspath(json_path)

  with open(json_path, 'w') as json_file:
    json.dump(json_data, json_file, **kwargs)


def format_number(numbers: list, ndigits: int = 4):
  return [round(float(n), ndigits) for n in numbers]

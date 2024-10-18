import os.path as osp
import sys


def is_running_in_bundle():
  return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_bundled_path(relpath: str = ''):
  prefix = sys._MEIPASS if is_running_in_bundle() else ''
  return osp.join(prefix, relpath) if prefix or relpath else ''

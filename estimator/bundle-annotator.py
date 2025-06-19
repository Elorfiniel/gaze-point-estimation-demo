# Enable multiprocessing for the bundled app, as described in the following links:
#   1. https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing
#   2. https://stackoverflow.com/questions/24944558/pyinstaller-built-windows-exe-fails-with-multiprocessing
if __name__ == '__main__':
  from multiprocessing import freeze_support
  freeze_support()  # Fix issues on Windows


from annotate.main_pass import ParallelEntryPass

from runtime.bundle import is_running_in_bundle, get_bundled_path
from runtime.es_config import EsConfig, EsConfigFns
from runtime.miscellaneous import deep_update
from runtime.log import runtime_logger

from annotator import collect_recordings

import argparse
import os.path as osp
import sys


rt_logger = runtime_logger(name='annotator')


def collect_an_config(cmdargs: argparse.Namespace):
  config_path = get_bundled_path(osp.join('_app_data', 'estimator.toml'))

  config_updater_path = osp.abspath(cmdargs.config)
  config_updater = EsConfig.from_toml(config_updater_path).to_dict()

  es_config_dict = EsConfig.from_toml(config_path, config_updater).to_dict()

  annot_config_path = osp.abspath(cmdargs.annot_config)
  annot_config_dict = EsConfig.from_toml(annot_config_path).to_dict()

  an_config = EsConfig(deep_update(es_config_dict, annot_config_dict))
  EsConfigFns.set_config_path(an_config, config_path)

  return an_config


def main_procedure(cmdargs: argparse.Namespace):
  if not is_running_in_bundle():
    rt_logger.error('this script should only be run from the bundled app')
    sys.exit(1) # Exit the execution

  record_path, recordings = collect_recordings(cmdargs)
  an_config = collect_an_config(cmdargs)
  ParallelEntryPass(record_path, recordings, an_config).run()


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Annotate the collected recordings automatically.')

  targets = parser.add_mutually_exclusive_group(required=True)
  targets.add_argument('--record-path', type=str, help='The path to the collected recordings.')
  targets.add_argument('--recording', type=str, help='The path to a specific recording.')

  parser.add_argument('--config', type=str, default='estimator-config.toml',
                      help='Device-specific configuration for this PoG estimator.')
  parser.add_argument('--annot-config', type=str, required=True,
                      help='Configuration for this PoG annotator.')

  main_procedure(parser.parse_args())

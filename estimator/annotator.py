from annotate.main_pass import ParallelEntryPass

from runtime.es_config import EsConfig, EsConfigFns
from runtime.miscellaneous import deep_update
from runtime.log import runtime_logger

import argparse
import os
import os.path as osp


rt_logger = runtime_logger(name='annotator')


def collect_recordings(cmdargs: argparse.Namespace):
  if cmdargs.record_path:
    record_path = osp.abspath(cmdargs.record_path)
    recordings = [
      item for item in os.listdir(record_path)
      if osp.isdir(osp.join(record_path, item))
    ]
  if cmdargs.recording:
    record_path = osp.dirname(osp.abspath(cmdargs.recording))
    recordings = [osp.basename(osp.abspath(cmdargs.recording))]

  recordings.sort(reverse=False)
  rt_logger.info(f'collected {len(recordings)} recordings from "{record_path}"')

  return record_path, recordings

def collect_an_config(cmdargs: argparse.Namespace):
  config_path = osp.abspath(cmdargs.config)
  es_config_dict = EsConfig.from_toml(config_path).to_dict()

  annot_config_path = osp.abspath(cmdargs.annot_config)
  annot_config_dict = EsConfig.from_toml(annot_config_path).to_dict()

  an_config = EsConfig(deep_update(es_config_dict, annot_config_dict))
  EsConfigFns.set_config_path(an_config, config_path)

  return an_config


def main_procedure(cmdargs: argparse.Namespace):
  record_path, recordings = collect_recordings(cmdargs)
  an_config = collect_an_config(cmdargs)
  ParallelEntryPass(record_path, recordings, an_config).run()


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Annotate the collected recordings automatically.')

  targets = parser.add_mutually_exclusive_group(required=True)
  targets.add_argument('--record-path', type=str, help='The path to the collected recordings.')
  targets.add_argument('--recording', type=str, help='The path to a specific recording.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for the PoG estimator.')
  parser.add_argument('--annot-config', type=str, required=True,
                      help='Configuration for this PoG annotator.')

  main_procedure(parser.parse_args())

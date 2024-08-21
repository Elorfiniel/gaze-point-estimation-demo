from tool_utils import (
  QuickRegistry, active_root_logger,
  parse_file_ext, parse_key_value,
  update_kwargs_by_pop,
)
from preview import (
  merge_image_labels, set_label_plot_style,
)

import argparse
import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
import os.path as osp
import sklearn.neighbors as skn


method_registry = QuickRegistry()

@method_registry.register(name='none')
def skip_cleaning(preds, groundtruth):
  return np.ones(shape=(len(preds), )).astype(bool)

@method_registry.register(name='lof')
def sklearn_lof_detector(preds, groundtruth, nn_ratio=0.40):
  lof = skn.LocalOutlierFactor(
    n_neighbors=max(int(nn_ratio * len(preds)), 1),
    contamination='auto',
  )
  judges = lof.fit_predict(preds)

  return judges == 1


def data_cleaning_with_method(method_name, merged_labels, out_folder,
                              min_preds_samples=4, min_total_samples=4,
                              **cfg_options):
  '''Data cleaning follows the steps below:

  1. Read and scatter plot the data for each Point-of-Gaze.
  2. Perform data cleaning on the data for each Point-of-Gaze.
  3. Scatter plot the cleaned data.
  4. Append calibration points to the cleaned data.
  5. Save the data for each Point-of-Gaze.

  Currently, each Point-of-Gaze is treated independently, rather than jointly.

  Note that each merged label is a dict with the following keys:
    - 'gts': ground-truth for the current Point-of-Gaze
    - 'preds': a list of predicted gaze points
    - 'ids': a list of image ids in correspondence to the 'preds'

  All the data are in string format. Convert them before processing.

  ``` python
  merged_label_a = {
    "gts": ["-5.2678", "-13.0902"],
    "preds": [
      ["-3.9965", "-9.7022"],
      ["-3.7003", "-9.1609"],
      ...
    ],
    "ids": [
      "00000",
      "00001",
      ...
    ],
  }
  ```
  '''

  kwargs = dict(
    preview=False,
    figsize=(10, 6),
    dpi=196,
    json_name='labels',
  )
  update_kwargs_by_pop(kwargs, cfg_options)

  is_calib = lambda p: p[0] == 0.0 and p[1] == 0.0
  all_preds = np.concatenate([
    np.array(m['preds'], dtype=np.float32) for m in merged_labels
  ], axis=0)
  all_preds = np.array([x for x in all_preds if not is_calib(x)])

  cleaned_labels = [] # a list of cleaned labels for each Point-of-Gaze

  # clean the data with the chosen method
  method_fn = method_registry[method_name]
  for mdx, merged_label in enumerate(merged_labels):
    if kwargs['preview']:
      fig, ax_label = plt.subplots(1, 1, figsize=kwargs['figsize'], dpi=kwargs['dpi'])
      set_label_plot_style(ax_label)

    groundtruth = np.array(merged_label['gts'], dtype=np.float32)

    preds = np.array(merged_label['preds'], dtype=np.float32)
    calib_ids = [id for pred, id in zip(preds, merged_label['ids']) if is_calib(pred)]
    preds_ids = [id for pred, id in zip(preds, merged_label['ids']) if not is_calib(pred)]
    preds = np.array([pred for pred in preds if not is_calib(pred)])

    if len(preds) >= min_preds_samples:
      masks = method_fn(preds, groundtruth)
    else: # filter out insufficient samples
      masks = np.zeros(shape=(len(preds), ), dtype=bool)
    valid_ids = [id for id, mask in zip(preds_ids, masks) if mask]

    if kwargs['preview']:
      ax_label.scatter(all_preds[:, 0], all_preds[:, 1], facecolor='gray', s=2.4)

      if len(valid_ids) > 0:
        valid_preds = np.array([pred for pred, mask in zip(preds, masks) if mask])
        ax_label.scatter(valid_preds[:, 0], valid_preds[:, 1], facecolor='firebrick', s=4.0)

      ax_label.set_title(f'PoG (gt): {", ".join(merged_label["gts"])}', fontsize='medium')

      figname = f'{mdx:05d} {"_".join(merged_label["gts"])} - {method_name}.png'
      fig.savefig(osp.join(out_folder, figname))
      plt.close(fig)  # explicitly close the figure to release memory

    if len(calib_ids) + len(valid_ids) >= min_total_samples:
      cleaned_ids = sorted(calib_ids + valid_ids)
      cleaned_preds = [
        merged_label['preds'][id]
        for id in map(lambda x: merged_label['ids'].index(x), cleaned_ids)
      ]
      cleaned_label = dict(gts=merged_label['gts'], preds=cleaned_preds, ids=cleaned_ids)
      cleaned_labels.append(cleaned_label)

  # save the cleaned data as json file
  json_file = osp.join(out_folder, f'{kwargs["json_name"]}.json')
  with open(json_file, 'w') as f:
    json.dump(cleaned_labels, f, indent=None)

def data_cleaning(in_folder, out_folder, image_ext, method, **cfg_options):
  '''Automatically clean up the data (eg. remove outliers).

  Currently, each Point-of-Gaze is treated independently, rather than jointly.
  Moreover, the data cleaning does not take into account the ground-truth,
  image features, and the calibration points. It follows a simple heuristic
  approach that removes PoGs with insufficient samples, or samples that are
  classified as outliers by the Local Outlier Factor.

  TODO: fix observed issues listed below.
    - a. samples with sharp head movements or closed eyes.
    - b. samples where predicted PoGs are randomly scattered,
      so that multiple clusters are formed.
  '''

  image_basenames = [
    item
    for item in os.listdir(in_folder)
    if item.endswith(image_ext)
  ]
  if not image_basenames:
    logging.warning(f'no images found in "{in_folder}", skipping "{out_folder}"')
    return
  merged_labels = merge_image_labels(image_basenames)

  try:  # create output folder for current recording
    os.makedirs(out_folder, exist_ok=True)
  except Exception as ex:
    logging.warning(f'cannot make output folder "{out_folder}", due to {ex}')

  kwargs = dict(min_preds_samples=4, min_total_samples=4)
  update_kwargs_by_pop(kwargs, cfg_options)

  if method_registry[method] is None:
    logging.warning(f'method "{method}" not implemented, skipping ...')
  else: # perform data cleaning
    data_cleaning_with_method(
      method, merged_labels, out_folder,
      **kwargs, **cfg_options,
    )


def main_procedure(cmdargs: argparse.Namespace):
  # collect all recordings under the given path
  if cmdargs.record_path:
    record_path = osp.abspath(cmdargs.record_path)
    recordings = [
      item
      for item in os.listdir(record_path)
      if osp.isdir(osp.join(record_path, item))
    ]
  if cmdargs.recording:
    record_path = osp.dirname(osp.abspath(cmdargs.recording))
    recordings = [osp.basename(osp.abspath(cmdargs.recording))]

  # collect extra configurations
  cfg_options = {k:v for k, v in cmdargs.cfg_options} if cmdargs.cfg_options else {}

  # perform data cleaning on each recording, if any
  if recordings:
    recordings.sort(reverse=False)
    try:  # make sure the output folder exists
      out_root = osp.abspath(cmdargs.out_folder)
      os.makedirs(out_root, exist_ok=True)
    except Exception as ex:
      logging.warning(f'cannot make output folder "{out_root}", due to {ex}')

  logging.info(f'collected {len(recordings)} recordings from "{record_path}"')

  for recording in recordings:
    in_folder = osp.join(record_path, recording)
    out_folder = osp.join(out_root, recording)
    data_cleaning(in_folder, out_folder, cmdargs.img_ext, cmdargs.method, **cfg_options)



if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Perform data cleaning on collected recordings.')

  parser.add_argument('--cfg-options', nargs='+', type=parse_key_value,
                      help='Extra configurations, e.g. --cfg-options "key=value".')
  parser.add_argument('--method', type=str, default='none', choices=['none', 'lof'],
                      help='Method to use for data cleaning.')

  targets = parser.add_mutually_exclusive_group(required=True)
  targets.add_argument('--record-path', type=str, help='The path to the stored recordings.')
  targets.add_argument('--recording', type=str, help='The path to a specific recording.')

  parser.add_argument('--img-ext', default='.jpg', type=parse_file_ext,
                      help='The extension of the image files.')
  parser.add_argument('--out-folder', type=str, default='output', help='Output folder.')

  active_root_logger()
  main_procedure(parser.parse_args())

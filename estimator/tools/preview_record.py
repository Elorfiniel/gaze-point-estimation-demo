import argparse
import logging
import functools
import numpy as np
import os
import os.path as osp

import matplotlib.animation as man
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


'''The following three functions parse the image names and generate
the merged labels. Each recording has a unique folder, where a list of
images named as "<image_id> <px>_<py>_<lx>_<ly>.jpg" are stored.

The purpose of these functions are to:

1. Parse the image_id, px, py, lx, ly from the image_basename.
2. Merge the labels for each target w.r.t. the label (lx, ly).

The final result is a list of merged_labels, where each merged_label
contains groundtruth for each target, a list of image_ids, and the
corresponding labels predicted for that image by the model.
'''
def parse_label(image_basename):
  root, ext = osp.splitext(image_basename)
  image_id, labels = root.split(sep=' ')
  labels = [x for x in labels.split(sep='_')]
  return image_id, *labels

def parse_group_counts(image_labels):
  group_counts = []

  label_equal = lambda p1, p2: p1[0] == p2[0] and p1[1] == p2[1]
  for image_id, px, py, lx, ly in image_labels:
    if group_counts and label_equal(group_counts[-1][0], (lx, ly)):
      group_counts[-1][1] += 1
    else:
      group_counts.append([(lx, ly), 1])

  return group_counts

def merge_image_labels(image_basenames):
  image_labels = [parse_label(x) for x in image_basenames]

  group_counts = parse_group_counts(image_labels)

  group_splits = [x[1] for x in group_counts]
  group_splits = [sum(group_splits[:i+1]) for i in range(len(group_splits))]
  group_splits = [0] + group_splits

  merged_labels = []  # each contains all labels for a single target
  for start, end, counts in zip(group_splits[:-1], group_splits[1:], group_counts):
    merged_labels.append({
      'gts': [x for x in counts[0]],
      'preds': [[y for y in x[1:3]] for x in image_labels[start:end]],
      'ids': [x[0] for x in image_labels[start:end]],
    })

  return merged_labels


'''Generate a video for each recording, so as to check the quality of
collected data in a straightforward manner.
'''
def plot_mean_circle(ax_label, valid_preds):
  mean_preds = np.mean(valid_preds, axis=0)
  mean_radius = np.mean(np.linalg.norm(valid_preds - mean_preds, axis=1))

  anchors = np.linspace(0.0, 2 * np.pi, 50)
  mean_Xs = np.cos(anchors) * mean_radius + mean_preds[0]
  mean_Ys = np.sin(anchors) * mean_radius + mean_preds[1]

  mean_line = ax_label.plot(
    mean_Xs, mean_Ys,
    color='lightskyblue',
    alpha=0.4, zorder=-10,
    linewidth=1.0, linestyle='--',
  )

  return mean_line

def plot_frame_artist_backend(image_path, label, pred=None,
                              fig='matplotlib.figure.Figure',
                              ax_image='matplotlib.axes.Axes',
                              ax_label='matplotlib.axes.Axes'):
  artists_image, artists_label = [], []

  axes_image = ax_image.imshow(plt.imread(image_path))
  artists_image.append(axes_image)

  if pred is not None:
    pred_line = ax_label.plot(
      (label[0], pred[0]),
      (label[1], pred[1]),
      color='lightskyblue',
      alpha=0.4, zorder=-10,
      linewidth=1.0, linestyle='--',
    )
    artists_label.extend(pred_line)

    pred_label = ax_label.add_patch(
      patches.Circle(pred, radius=0.32, facecolor='lightskyblue', edgecolor='none', alpha=0.6)
    )
    artists_label.append(pred_label)

  true_label = ax_label.add_patch(
    patches.Circle(
      label, radius=0.24, edgecolor='none', alpha=1.0,
      facecolor='firebrick' if pred is not None else 'limegreen',
    )
  )
  artists_label.append(true_label)

  return artists_image, artists_label

def gv_artist_backend(fig, ax_image, ax_label, merged_labels, in_folder, image_ext):
  '''This backend comsumes huge memory, thus not recommended.'''

  is_calib = lambda p: p[0] == 0.0 and p[1] == 0.0
  plot_frame = functools.partial(
    plot_frame_artist_backend,
    fig=fig, ax_image=ax_image, ax_label=ax_label,
  )

  artists = []  # a collection of artists for each frame
  for merged_label in merged_labels:
    # create common artists for each target
    all_preds = np.array(merged_label['preds'], dtype=np.float32)
    valid_preds = np.array([x for x in all_preds if not is_calib(x)])

    artists_common = []
    for pred in valid_preds:
      pred_label = ax_label.add_patch(
        patches.Circle(pred, radius=0.18, facecolor='gray', edgecolor='none', alpha=0.4)
      )
      artists_common.append(pred_label)

    if len(valid_preds) > 1:
      mean_line = plot_mean_circle(ax_label, valid_preds)
      artists_common.extend(mean_line)

    # create artists for each image
    for image_id, pred in zip(merged_label['ids'], merged_label['preds']):
      image_basename = f"{image_id} {'_'.join(pred + merged_label['gts'])}" + image_ext
      image_path = osp.join(in_folder, image_basename)

      true_label = np.array(merged_label['gts'], dtype=np.float32)

      pred_label = np.array(pred, dtype=np.float32)
      pred_label = pred_label if not is_calib(pred_label) else None

      artists_image, artists_label = plot_frame(image_path, true_label, pred_label)
      artists.append(artists_image + artists_common + artists_label)

  return man.ArtistAnimation(fig, artists, interval=160)

def plot_frame_function_backend(generated_params, global_context,
                                fig='matplotlib.figure.Figure',
                                ax_image='matplotlib.axes.Axes',
                                ax_label='matplotlib.axes.Axes'):

  image_path, label, pred, valid_preds = generated_params
  image = plt.imread(image_path)

  pred_center = pred if pred is not None else np.array([-99.99, -99.99])
  label_color = 'firebrick' if pred is not None else 'limegreen'

  # create common artists for each target
  previous_valid_preds = global_context.get('valid_preds', None)
  if previous_valid_preds is not None and previous_valid_preds is not valid_preds:
    # clear cached artists
    for other_pred in global_context['other_pred_labels']:
      other_pred.remove()
    for line2d in global_context['mean_line']:
      line2d.remove()

  if previous_valid_preds is None or previous_valid_preds is not valid_preds:
    # create new artists in case of either first frame or new valid predictions
    global_context['valid_preds'] = valid_preds
    if len(valid_preds) > 1:
      mean_line = plot_mean_circle(ax_label, valid_preds)
      global_context['mean_line'] = mean_line
    else:
      global_context['mean_line'] = []

    global_context['other_pred_labels'] = []
    for other_pred in valid_preds:
      pred_label = ax_label.add_patch(
        patches.Circle(other_pred, radius=0.18, facecolor='gray', edgecolor='none', alpha=0.4)
      )
      global_context['other_pred_labels'].append(pred_label)

  # create artists for each image
  if global_context.get('axes_image', None):
    for line2d in global_context['pred_line']:
      line2d.remove()

  if pred is not None:
    global_context['pred_line'] = ax_label.plot(
      (label[0], pred[0]),
      (label[1], pred[1]),
      color='lightskyblue',
      alpha=0.4, zorder=-10,
      linewidth=1.0, linestyle='--',
    )
  else:
    global_context['pred_line'] = []

  if global_context.get('axes_image', None) is None:
    # first frame, initialize axes and artists
    global_context['axes_image'] = ax_image.imshow(image)
    global_context['pred_label'] = ax_label.add_patch(
      patches.Circle(pred_center, radius=0.32, facecolor='lightskyblue', edgecolor='none', alpha=0.6)
    )
    global_context['true_label'] = ax_label.add_patch(
      patches.Circle(label, radius=0.24, edgecolor='none', alpha=1.0, facecolor=label_color)
    )

  else: # update existing artists
    global_context['axes_image'].set_data(image)
    global_context['pred_label'].set_center(pred_center)
    global_context['true_label'].set_center(label)
    global_context['true_label'].set_facecolor(label_color)

def gv_function_backend(fig, ax_image, ax_label, merged_labels, in_folder, image_ext):
  '''This backend makes changes to each frame iteratively, thus more efficient.'''

  is_calib = lambda p: p[0] == 0.0 and p[1] == 0.0
  plot_frame = functools.partial(
    plot_frame_function_backend,
    global_context=dict(),
    fig=fig, ax_image=ax_image, ax_label=ax_label,
  )

  def params_generator():
    for merged_label in merged_labels:
      all_preds = np.array(merged_label['preds'], dtype=np.float32)
      valid_preds = np.array([x for x in all_preds if not is_calib(x)])

      for image_id, pred in zip(merged_label['ids'], merged_label['preds']):
        image_basename = f"{image_id} {'_'.join(pred + merged_label['gts'])}" + image_ext
        image_path = osp.join(in_folder, image_basename)

        true_label = np.array(merged_label['gts'], dtype=np.float32)

        pred_label = np.array(pred, dtype=np.float32)
        pred_label = pred_label if not is_calib(pred_label) else None

        yield image_path, true_label, pred_label, valid_preds

  max_frames = sum([len(x['ids']) for x in merged_labels])

  return man.FuncAnimation(
    fig, plot_frame, params_generator(),
    save_count=max_frames, interval=160,
  )

def generate_visualization(in_folder, out_file, image_ext='.jpg', func_anim=True, **kwargs):
  logging.info(f'in_folder: "{in_folder}"')

  image_basenames = [
    item
    for item in os.listdir(in_folder)
    if item.endswith(image_ext)
  ]
  if not image_basenames:
    logging.warn(f'no images found in "{in_folder}", skipping "{out_file}"')
    return
  merged_labels = merge_image_labels(image_basenames)

  fig, (ax_image, ax_label) = plt.subplots(1, 2, figsize=(13, 6))
  fig.subplots_adjust(left=0.08, right=0.90)
  set_image_plot_style(ax_image)
  set_label_plot_style(ax_label)

  backend = gv_function_backend if func_anim else gv_artist_backend
  animate = backend(fig, ax_image, ax_label, merged_labels, in_folder, image_ext)

  logging.info(f'out_file: "{out_file}"')
  animate.save(out_file, writer='ffmpeg')


'''The following functions are used to plot the images and labels.
Specifically, they set the plot style, and plot the results.
'''
def set_image_plot_style(ax_image):
  ax_image.set_axis_off()

def set_label_plot_style(ax_label):
  ax_label.set(
    xlim=[-20.0, 20.0], ylim=[-20.0, 0.0],
    xticks=np.arange(-20.0, 20.0 + 0.01, 2.0),
    yticks=np.arange(-20.0, 0.0 + 0.01, 2.0),
    aspect='equal',
  )

  ax_label.tick_params(
    direction='in', length=4.0,
    bottom=True, top=True,
    left=True, right=True,
    labelbottom=True, labeltop=True,
    labelleft=True, labelright=True,
    labelsize=6.0,
  )

  formatter = ticker.FuncFormatter(lambda v, _: f'{v:+.1f}')
  ax_label.xaxis.set_major_formatter(formatter)
  ax_label.yaxis.set_major_formatter(formatter)

  spine_style = dict(visible=True, color='k', alpha=0.8)
  ax_label.spines.bottom.set(position=('axes', 0.0), **spine_style)
  ax_label.spines.top.set(position=('axes', 1.0), **spine_style)
  ax_label.spines.left.set(position=('axes', 0.0), **spine_style)
  ax_label.spines.right.set(position=('axes', 1.0), **spine_style)

  grid_style = dict(visible=True, color='k', alpha=0.2)
  ax_label.grid(which="both", axis="both", **grid_style)


'''Main procedure for commandline invocation.
'''
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

  # collect visualization settings
  visual_kwargs = {k:v for k, v in cmdargs.visual_kwargs} if cmdargs.visual_kwargs else {}

  # generate visualization for each recording, if any
  if recordings:
    recordings.sort(reverse=False)
    try:  # make sure the output folder exists
      out_folder = osp.abspath(cmdargs.out_folder)
      os.makedirs(out_folder, exist_ok=True)
    except Exception as ex:
      logging.warn(f'cannot make output folder "{out_folder}", due to {ex}')

  logging.info(f'collected {len(recordings)} recordings from "{record_path}"')

  for recording in recordings:
    in_folder = osp.join(record_path, recording)
    out_file = osp.join(out_folder, f'{recording}.mp4')
    generate_visualization(in_folder, out_file, **visual_kwargs)



def active_root_logger():
  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(logging.INFO)

  formatter = logging.Formatter(
    '[ %(asctime)s ] process %(process)d - %(levelname)s: %(message)s',
    datefmt='%m-%d %H:%M:%S',
  )
  stream_handler.setFormatter(formatter)

  root_logger = logging.getLogger('')
  for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
  root_logger.addHandler(stream_handler)
  root_logger.setLevel(logging.INFO)

def parse_key_value(kv_string: str):
  try:  # split the key-value pair
    key, value = kv_string.split(sep='=', maxsplit=1)
    return key, value
  except ValueError:
    raise argparse.ArgumentTypeError(f"invalid key-value pair '{kv_string}', expecting 'key=value'")

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='visualize data captured with the gaze demo')

  parser.add_argument('--visual-kwargs', nargs='+', type=parse_key_value,
                      help='Visualization settings, e.g. --visual-kwargs "key=value".')

  targets = parser.add_mutually_exclusive_group(required=True)
  targets.add_argument('--record-path', type=str, help='The path to the stored recordings.')
  targets.add_argument('--recording', type=str, help='The path to the recording to visualize.')

  parser.add_argument('--out-folder', type=str, default='output', help='Output folder.')

  active_root_logger()
  main_procedure(parser.parse_args())

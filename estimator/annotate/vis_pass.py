from .base_pass import BasePass
from .miscellaneous import require_context

from runtime.es_config import EsConfig, EsConfigFns

import functools
import matplotlib.animation as man
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os.path as osp


def set_image_plot_style(ax_image, vis_config):
  ax_image.set_axis_off()

def set_axes_splines_style(ax, style):
  ax.spines.bottom.set(position=('axes', 0.0), **style)
  ax.spines.top.set(position=('axes', 1.0), **style)
  ax.spines.left.set(position=('axes', 0.0), **style)
  ax.spines.right.set(position=('axes', 1.0), **style)

def set_label_plot_style(ax_label, vis_config):
  xlim = vis_config['limits']['x']
  ylim = vis_config['limits']['y']

  ax_label.set(
    xlim=xlim, ylim=ylim,
    xticks=np.arange(xlim[0], xlim[1] + 0.01, 2.0),
    yticks=np.arange(ylim[0], ylim[1] + 0.01, 2.0),
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
  set_axes_splines_style(ax_label, spine_style)

  grid_style = dict(visible=True, color='k', alpha=0.2)
  ax_label.grid(which="both", axis="both", **grid_style)

def create_preview_plots(vis_config):
  fig, (ax_image, ax_label) = plt.subplots(1, 2, figsize=vis_config['figsize'])
  fig.subplots_adjust(**vis_config['subplots_adjust'])
  set_image_plot_style(ax_image, vis_config)
  set_label_plot_style(ax_label, vis_config)
  return fig, ax_image, ax_label

def function_plot_frame(frame_params, context, fig, ax_image, ax_label):
  '''Visualize the status of each frame with functional animation backend

  Note that the frame_params contains the following parameters:
    - image_path: path to the image captured when gazing at the target
    - target: target location, aka. groundtruth
    - pseudo: pseudo-label location, used for outlier detection
    - okay: whether the current frame is treated as a good sample
    - pseudos: list of pseudo-labels for current target

  For details on the plotting, please refer to the implementation of
  `FunctionAnimContext` and the `VisualizePass`
  '''

  # Display the image captured when gazing at the target
  context.display_image(ax_image, plt.imread(frame_params['image_path']))

  # Display all the pseudo-labels for current target (gray dots)
  okay, pseudos = frame_params['okay'], frame_params['pseudos']
  context.display_context(ax_label, okay, pseudos)

  # Display the target (red dot) and the pseudo-label (blue dot)
  target, pseudo = frame_params['target'], frame_params['pseudo']
  context.display_label(ax_label, target, pseudo, okay)

def function_animation(frame_params, fig, ax_image, ax_label):
  plot_frame = functools.partial(
    function_plot_frame,
    context=FunctionAnimContext(),
    fig=fig, ax_image=ax_image, ax_label=ax_label,
  )
  return man.FuncAnimation(fig, plot_frame, frame_params, interval=160)

def close_preview_plots(fig):
  plt.close(fig)  # Explicitly close the figure to release memory


class FunctionAnimContext:
  def __init__(self):
    self.axes_image = None

    self.patches_label = dict(target=None, pseudo=None, conn=None)
    self.target_style = dict(radius=0.24, edgecolor='none', alpha=1.0)
    self.pseudo_style = dict(
      radius=0.32, facecolor='lightskyblue',
      edgecolor='none', alpha=0.6,
    )
    self.conn_style = dict(
      color='lightskyblue',
      alpha=0.4, zorder=-10,
      linewidth=1.0, linestyle='--',
    )

    self.patches_ctx = dict(okay=None, pseudos=[], mcircle=[])
    self.pseudos_style = dict(
      radius=0.18, facecolor='gray',
      edgecolor='none', alpha=0.4,
    )
    self.mcircle_style = dict(
      color='lightskyblue',
      alpha=0.4, zorder=-10,
      linewidth=1.0, linestyle='--',
    )

  def display_image(self, ax, image):
    if self.axes_image is None:
      self.axes_image = ax.imshow(image)
    else:
      self.axes_image.set_data(image)

  def display_context(self, ax, okay, pseudos):
    spines_style = dict(
      visible=True, alpha=0.8,
      color='limegreen' if okay else 'firebrick',
      linewidth=1.0 if okay else 1.4,
    )
    set_axes_splines_style(ax, spines_style)

    for p in self.patches_ctx['pseudos']: p.remove()
    self.patches_ctx['pseudos'].clear()
    for pseudo in pseudos:
      p = ax.add_patch(patches.Circle(pseudo, **self.pseudos_style))
      self.patches_ctx['pseudos'].append(p)

    for l in self.patches_ctx['mcircle']: l.remove()
    self.patches_ctx['mcircle'].clear()
    if len(pseudos) > 1:
      pseudos = np.array(pseudos, dtype=np.float32)

      mean_c = np.mean(pseudos, axis=0)
      mean_r = np.mean(np.linalg.norm(pseudos - mean_c, axis=1))

      anchors = np.linspace(0.0, 2 * np.pi, 50)
      mean_xs = np.cos(anchors) * mean_r + mean_c[0]
      mean_ys = np.sin(anchors) * mean_r + mean_c[1]

      mcircle = ax.plot(mean_xs, mean_ys, **self.mcircle_style)
      self.patches_ctx['mcircle'] = mcircle

  def display_label(self, ax, target, pseudo, okay):
    if self.patches_label['target'] is None:
      p = ax.add_patch(patches.Circle(target, **self.target_style))
      self.patches_label['target'] = p
    else:
      self.patches_label['target'].set_center(target)
    target_fc = 'limegreen' if okay else 'firebrick'
    self.patches_label['target'].set_facecolor(target_fc)

    if pseudo is None and self.patches_label['pseudo'] is not None:
      self.patches_label['pseudo'].remove()
      self.patches_label['pseudo'] = None
      self.patches_label['conn'].remove()
      self.patches_label['conn'] = None
    elif pseudo is not None:
      xdata, ydata = (target[0], pseudo[0]), (target[1], pseudo[1])
      if self.patches_label['pseudo'] is None:
        p = ax.add_patch(patches.Circle(pseudo, **self.pseudo_style))
        self.patches_label['pseudo'] = p
        p = ax.plot(xdata, ydata, **self.conn_style)[0]
        self.patches_label['conn'] = p
      else:
        self.patches_label['pseudo'].set_center(pseudo)
        self.patches_label['conn'].set_data(xdata, ydata)


class VisualizePass(BasePass):

  PASS_NAME = 'vis_pass.visualize'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def before_pass(self, context: dict, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'vis_pass')

    fig, ax_image, ax_label = create_preview_plots(pass_config)
    self.plots = dict(fig=fig, ax_image=ax_image, ax_label=ax_label)
    self.frame_params = []  # Params of each frame

  def after_pass(self, context: dict, **kwargs):
    anim_path = osp.join(self.recording_path, 'labels.mp4')

    function_animation(
      frame_params=self.frame_params, **self.plots,
    ).save(anim_path, writer='ffmpeg')

    close_preview_plots(self.plots['fig'])

  def collect_data(self, context: dict, **kwargs):
    return context['labels']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]
    pseudos = [p for p in data['pogs'] if p is not None]

    for image_name, pseudo, okay in zip(image_names, data['pogs'], data['okay']):
      self.frame_params.append(dict(
        image_path=osp.join(self.recording_path, image_name),
        target=[data['lx'], data['ly']],
        pseudo=pseudo, okay=okay, pseudos=pseudos,
      ))

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['labels'])
    super().run(context=context, **kwargs)

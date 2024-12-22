import functools
import matplotlib.animation as man
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


__all__ = [
  'create_preview_plots',
  'function_animation',
  'close_preview_plots',
]


'''The following functions are used to plot the images and labels.
Specifically, they set the plot style, and plot the results.
'''
def _set_image_plot_style(ax_image, config):
  ax_image.set_axis_off()

def _set_axes_splines_style(ax, style):
  ax.spines.bottom.set(position=('axes', 0.0), **style)
  ax.spines.top.set(position=('axes', 1.0), **style)
  ax.spines.left.set(position=('axes', 0.0), **style)
  ax.spines.right.set(position=('axes', 1.0), **style)

def _set_label_plot_style(ax_label, config):
  xlim = config['limits']['x']
  ylim = config['limits']['y']

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
  _set_axes_splines_style(ax_label, spine_style)

  grid_style = dict(visible=True, color='k', alpha=0.2)
  ax_label.grid(which="both", axis="both", **grid_style)


'''Generate a video for each recording, so as to check the quality of
collected data in a straightforward manner.
'''
def _plot_mean_circle(ax, pseudo_list, **mean_circle_style):
  pseudo_list = np.array(pseudo_list, dtype=np.float32)

  mean_c = np.mean(pseudo_list, axis=0)
  mean_r = np.mean(np.linalg.norm(pseudo_list - mean_c, axis=1))

  anchors = np.linspace(0.0, 2 * np.pi, 50)
  mean_Xs = np.cos(anchors) * mean_r + mean_c[0]
  mean_Ys = np.sin(anchors) * mean_r + mean_c[1]

  lines = ax.plot(mean_Xs, mean_Ys, **mean_circle_style)

  return lines

class _FunctionAnimContext:
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

    self.patches_ctx = dict(okay=None, pseudo_list=[], mean_circle=[])
    self.pseudo_list_style = dict(
      radius=0.18, facecolor='gray',
      edgecolor='none', alpha=0.4,
    )
    self.mean_circle_style = dict(
      color='lightskyblue',
      alpha=0.4, zorder=-10,
      linewidth=1.0, linestyle='--',
    )

  def display_image(self, ax, image):
    if self.axes_image is None:
      self.axes_image = ax.imshow(image)
    else:
      self.axes_image.set_data(image)

  def display_context(self, ax, okay, pseudo_list):
    spines_style = dict(
      visible=True, alpha=0.8,
      color='limegreen' if okay else 'firebrick',
      linewidth=1.0 if okay else 1.4,
    )
    _set_axes_splines_style(ax, spines_style)

    for p in self.patches_ctx['pseudo_list']: p.remove()
    self.patches_ctx['pseudo_list'].clear()
    for pseudo in pseudo_list:
      p = ax.add_patch(patches.Circle(pseudo, **self.pseudo_list_style))
      self.patches_ctx['pseudo_list'].append(p)

    for l in self.patches_ctx['mean_circle']: l.remove()
    self.patches_ctx['mean_circle'].clear()
    if len(pseudo_list) > 1:
      mean_circle = _plot_mean_circle(ax, pseudo_list, **self.mean_circle_style)
      self.patches_ctx['mean_circle'] = mean_circle

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


def create_preview_plots(config):
  fig, (ax_image, ax_label) = plt.subplots(1, 2, figsize=config['figsize'])
  fig.subplots_adjust(**config['subplots_adjust'])
  _set_image_plot_style(ax_image, config)
  _set_label_plot_style(ax_label, config)
  return fig, ax_image, ax_label

def function_plot_frame(frame_params, context, fig, ax_image, ax_label):
  '''Visualize the status of each frame with functional animation backend.

  Note that the frame_params contains the following parameters:
    - image_path: path to the image captured when gazing at the target
    - target: target location, aka. groundtruth
    - pseudo: pseudo-label location, used for outlier detection
    - okay: whether the current frame is treated as a good sample
    - pseudo_list: list of pseudo-labels for current target

  For details on the plotting, please refer to the implementation of
  `_FunctionAnimContext` and the `VisualizePass`.
  '''

  # Display the image captured when gazing at the target
  image_path = frame_params['image_path']
  context.display_image(ax_image, plt.imread(image_path))
  # Display all the pseudo-labels for current target (gray dots)
  okay, pseudo_list = frame_params['okay'], frame_params['pseudo_list']
  context.display_context(ax_label, okay, pseudo_list)
  # Display the target (red dot) and the pseudo-label (blue dot)
  target, pseudo = frame_params['target'], frame_params['pseudo']
  context.display_label(ax_label, target, pseudo, okay)

def function_animation(params_list, fig, ax_image, ax_label):
  plot_frame = functools.partial(
    function_plot_frame,
    context=_FunctionAnimContext(),
    fig=fig, ax_image=ax_image, ax_label=ax_label,
  )
  return man.FuncAnimation(fig, plot_frame, params_list, interval=160)

def close_preview_plots(fig):
  plt.close(fig)  # Explicitly close the figure to release memory

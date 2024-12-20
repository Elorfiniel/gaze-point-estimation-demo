import cv2


class Transforms:

  _TRANSFORMS = {}  # {name: transform}

  def __init__(self, **transform_config):
    self.transforms = []

    sort_fn = lambda k: transform_config[k]['index']
    for key in sorted(transform_config, key=sort_fn):
      config = transform_config[key]
      kwargs = {k:v for k, v in config.items() if k != 'index'}
      transform = self._TRANSFORMS[key](**kwargs)
      self.transforms.append(transform)

  @classmethod
  def register(cls, obj=None, *, name='', force=False):
    '''Register transform function in the registry table.

    ```
    @Transforms.register
    class TransformFn1:
      ...

    @Transforms.register(name='CustomName')
    class TransformFn2:
      ...

    # Registry: {'TransformFn1': ..., 'CustomName': ...}
    ```

    `obj`: the callable to be registered in registry table.

    `name`: an optional name for the callable, which replaces the `__name__` property.
    Note that this argument must be passed in as a keyword argument.

    `force`: force registering when an object with the same name already exists.
    Note that this argument must be passed in as a keyword argument.
    '''

    def register_fn(_obj):
      assert callable(_obj), 'object to be registerd must be a callable'
      assert hasattr(_obj, '__name__'), 'object to be registerd must have a name'

      name_registered = name or getattr(_obj, '__name__')
      if not name_registered in cls._TRANSFORMS or force:
        cls._TRANSFORMS[name_registered] = _obj

    if obj is None:
      return register_fn
    else:
      register_fn(obj)

  def transform(self, image):
    '''Transform image of shape (h, w, c).'''

    for t in self.transforms:
      image = t.transform(image)
    return image


def rescale_frame(image, src_res, tgt_res, resize=True):
  '''Rescale source resolution to target resolution (crop + resize).'''

  src_asp = src_res[1] / src_res[0]
  tgt_asp = tgt_res[1] / tgt_res[0]

  if tgt_asp > src_asp:
    rescale_h = int(src_res[1] / tgt_asp)
    padding_h = (src_res[0] - rescale_h) // 2
    image = image[padding_h:-padding_h, :]
  if tgt_asp < src_asp:
    rescale_w = int(src_res[0] * tgt_asp)
    padding_w = (src_res[1] - rescale_w) // 2
    image = image[:, padding_w:-padding_w]

  if resize:
    dsize = (tgt_res[1], tgt_res[0])
    image = cv2.resize(image, dsize, interpolation=cv2.INTER_CUBIC)

  return image

def denoise_frame(image, h_lumin, h_color, psize=7, wsize=21):
  '''Fast non-local means denoising for colored images.'''
  return cv2.fastNlMeansDenoisingColored(image, None, h_lumin, h_color, psize, wsize)

def create_clahe(clip_limit=2.0, grid_size=(8, 8)):
  '''Create CLAHE object for adaptive histogram equalization.'''
  return cv2.createCLAHE(clip_limit, grid_size)

def equalize_frame(image, clahe, to_lab=cv2.COLOR_BGR2LAB, to_img=cv2.COLOR_LAB2BGR):
  '''Adaptive histogram equalization for colored images, using CLAHE algorithm.'''

  image = cv2.cvtColor(image, to_lab)
  L, A, B = cv2.split(image)
  image = cv2.merge([clahe.apply(L), A, B])
  image = cv2.cvtColor(image, to_img)

  return image


@Transforms.register(name='rescale')
class Rescale:
  def __init__(self, **transform_config):
    self.transform_config = transform_config

  def transform(self, image):
    return rescale_frame(image, image.shape[:2], **self.transform_config)

@Transforms.register(name='denoise')
class Denoise:
  def __init__(self, **transform_config):
    self.transform_config = transform_config

  def transform(self, image):
    return denoise_frame(image, **self.transform_config)

@Transforms.register(name='equalize')
class Equalize:
  def __init__(self, ccode='bgr', clahe=dict()):
    assert ccode in ['bgr', 'rgb']

    if ccode == 'rgb':
      to_lab, to_img = cv2.COLOR_RGB2LAB, cv2.COLOR_LAB2RGB
    if ccode == 'bgr':
      to_lab, to_img = cv2.COLOR_BGR2LAB, cv2.COLOR_LAB2BGR

    self.clahe = create_clahe(**clahe)
    self.cvt = dict(to_lab=to_lab, to_img=to_img)

  def transform(self, image):
    return equalize_frame(image, self.clahe, **self.cvt)

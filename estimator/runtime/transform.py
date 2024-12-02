from runtime.miscellaneous import rescale_frame


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


@Transforms.register(name='rescale')
class Rescale:
  def __init__(self, **transform_config):
    self.transform_config = transform_config

  def transform(self, image):
    return rescale_frame(image, image.shape[:2], **self.transform_config)

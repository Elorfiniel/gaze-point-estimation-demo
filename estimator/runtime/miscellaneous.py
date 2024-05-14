import cv2
import logging
import json
import os
import toml


def configure_logging(level=logging.INFO, force=False):
  logging.basicConfig(
    level=level, force=force,
    format='[ %(asctime)s ] process %(process)d - %(levelname)s: %(message)s',
    datefmt='%m-%d %H:%M:%S',
  )


def load_toml_secure(toml_path):
  '''Load toml file with caution, return None if failed.'''

  toml_data = None

  if os.path.isfile(toml_path):
    with open(toml_path, 'r') as toml_file:
      try:
        toml_data = toml.load(toml_file)
      except:
        toml_data = None

  if toml_data is None:
    logging.error(f'cannot load from TOML file "{toml_path}"')

  return toml_data


def shrink_frame(image, src_res, tgt_res):
  '''Shrink a larger source resolution to a smaller resolution that fits within.'''
  assert src_res[0] >= tgt_res[0] and src_res[1] >= tgt_res[1]

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

  dsize = (tgt_res[1], tgt_res[0])
  image = cv2.resize(image, dsize, interpolation=cv2.INTER_CUBIC)

  return image


async def websocket_send_json(websocket, message_obj):
  await websocket.send(json.dumps(message_obj))

from .miscellaneous import deep_update, load_toml_secure

import copy
import pprint


class EsConfig:

  @classmethod
  def from_toml(cls, toml_path, config_updater: dict = None):
    es_config = load_toml_secure(toml_path)

    if isinstance(config_updater, dict):
      if es_config is not None:
        es_config = deep_update(es_config, config_updater)
      else:
        es_config = config_updater

    return cls(es_config) if es_config is not None else None

  def __init__(self, config_dict: dict):
    assert isinstance(config_dict, dict)
    self._config_dict = config_dict

  def __getitem__(self, key):
    if key not in self._config_dict:
      raise KeyError(f'key "{key}" not found in es config')

    value = self._config_dict[key]

    if isinstance(value, dict):
      return EsConfig(value)
    else:
      return copy.deepcopy(value)

  def __repr__(self):
    return f'EsConfig({pprint.pformat(self._config_dict, depth=1, compact=True)})'

  def to_dict(self):
    return copy.deepcopy(self._config_dict)


class EsConfigFns:
  '''Helper functions for estimator configuration.'''

  @staticmethod
  def named_dict(es_config: EsConfig, name: str) -> dict:
    config_or_value = es_config[name]
    if isinstance(config_or_value, EsConfig):
      return config_or_value.to_dict()
    return {name: config_or_value}

  @staticmethod
  def http_server_addr(es_config: EsConfig) -> dict:
    return es_config['server']['http'].to_dict()

  @staticmethod
  def ws_server_addr(es_config: EsConfig) -> dict:
    return es_config['server']['websocket'].to_dict()

  @staticmethod
  def open_browser(es_config: EsConfig) -> bool:
    return es_config['server']['browser']

  @staticmethod
  def set_config_path(es_config: EsConfig, config_path: str):
    setattr(es_config, 'config_path', config_path)

  @staticmethod
  def get_config_path(es_config: EsConfig) -> str:
    return getattr(es_config, 'config_path')

  @staticmethod
  def topleft_offset(es_config: EsConfig) -> list:
    return es_config['inference']['topleft_offset']

  @staticmethod
  def screen_size_px(es_config: EsConfig) -> list:
    return es_config['inference']['screen_size_px']

  @staticmethod
  def screen_size_cm(es_config: EsConfig) -> list:
    return es_config['inference']['screen_size_cm']

  @staticmethod
  def record_path(es_config: EsConfig) -> str:
    return es_config['server']['record']['path']

  @staticmethod
  def record_mode(es_config: EsConfig) -> bool:
    return EsConfigFns.record_path(es_config) != ''

  @staticmethod
  def collect_game_settings(es_config: EsConfig) -> dict:
    game_settings = EsConfigFns.named_dict(es_config, 'game')

    if game_settings['check']['camera']:
      game_settings['check']['src_res'] = es_config['capture']['resolution']
      game_settings['check']['tgt_res'] = es_config['transform']['rescale']['tgt_res']

    return game_settings

  @staticmethod
  def record_without_inference(es_config) -> bool:
    infer = es_config['server']['record']['inference']
    return EsConfigFns.record_mode(es_config) and not infer

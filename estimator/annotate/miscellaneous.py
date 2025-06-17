from .base_pass import BasePass


def require_context(bpass: BasePass, context: dict, item_names: list):
  for item_name in item_names:
    if context.get(item_name) is None:
      raise RuntimeError(f'{bpass.PASS_NAME} requires "{item_name}" in context')

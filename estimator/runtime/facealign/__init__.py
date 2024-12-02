# Bypass failure to import mediapipe, useful when the user cannot install it
# but wants to use the estimator in record mode (KeyAiming only)

try:
  import mediapipe as mp
  from .real import FaceAlignment
except ImportError:
  from .fake import FaceAlignment


__all__ = ['FaceAlignment']

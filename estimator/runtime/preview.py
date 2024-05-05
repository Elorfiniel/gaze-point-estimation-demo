import cv2  # OpenCV-Python


def create_pv_canvas(frame, background, pv_mode, pv_items):
  if pv_mode == 'none': return None

  if pv_mode == 'full':
    canvas = background.copy()

    if 'frame' in pv_items:
      ph, pw, _ = frame.shape
      tw = 480
      th = int(tw * ph / pw)
      canvas[:th, :tw] = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_CUBIC)

  if pv_mode == 'frame':
    canvas = frame.copy()

  return canvas


def _display_text_on_canvas(canvas, text, location):
  cv2.putText(
    canvas, text, location, cv2.FONT_HERSHEY_PLAIN, 1.6,
    color=(0, 0, 255), thickness=2, lineType=cv2.LINE_AA,
  )

def display_gaze_on_canvas(canvas, gx, gy, pv_mode, pv_items):
  if pv_mode == 'none': return False

  if pv_mode == 'full' and 'gaze' in pv_items:
    cv2.circle(canvas, (gx, gy), radius=56, color=(0, 0, 255), thickness=4, lineType=cv2.LINE_AA)

  if pv_mode == 'frame' and 'gaze' in pv_items:
    _display_text_on_canvas(canvas, f'gx: {gx}, gy: {gy}', (40, 60))

  return True

def display_time_on_canvas(canvas, time, pv_mode, pv_items):
  if pv_mode == 'none': return False

  if 'time' in pv_items:
    text = f'time: {time:.2f}s, fps: {1.0 / time:.2f}'
    _display_text_on_canvas(canvas, text, (40, canvas.shape[0] - 40))

    return True

def display_warning_on_canvas(canvas, pv_mode, pv_items):
  if pv_mode == 'none': return False

  if 'warn' in pv_items:
    text = 'no face detected ...'
    _display_text_on_canvas(canvas, text, (40, canvas.shape[0] - 40))

    return True


def display_canvas(pv_window, canvas, pv_mode, pv_items):
  if pv_mode == 'none': return False

  cv2.imshow(pv_window, canvas)
  is_exit = cv2.waitKey(6) & 0xFF == ord('X')

  return is_exit

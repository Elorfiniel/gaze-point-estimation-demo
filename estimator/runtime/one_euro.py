# From: https://gitee.com/elorfiniel/gaze-point-estimation-2023/blob/master/source/utils/common/one_euro.py
# Commit: 8797c10abcf35165cb2ffc0c6a46a72b684e7eb4
# Author: Elorfiniel (markgenthusiastic@gmail.com)

import math, time


class OneEuroFilter():
  def __init__(self, beta=0.0, d_cutoff=1.0, min_cutoff=1.0, clock=False):
    '''Filter noisy signals in real-time using 1-EUR filter.
    See also: https://gery.casiez.net/1euro/.

    `beta`: the speed coefficient.

    `d_cutoff`: the constant cutoff frequency.

    `min_cutoff`: the minimum cutoff frequency.

    `clock`: whether to use wall clock if timestamp is omitted.
    '''

    self._beta = beta
    self._d_cutoff = d_cutoff
    self._m_cutoff = min_cutoff

    self._sig = None
    self._dsig = None
    self._time = None

    self._use_clock = clock

  def _alpha(self, te, fc):
    a = 2 * math.pi * te * fc
    alpha = a / (1.0 + a)
    return alpha

  def _alpha_blend(self, alpha, x_new, x_old):
    return alpha * x_new + (1.0 - alpha) * x_old

  def filter(self, signal, timestamp=None):
    if timestamp is None:
      if self._use_clock: timestamp = time.time()
      else: raise RuntimeError(f'missing timestamp in one euro filtering')

    if self._sig is not None:
      te = timestamp - self._time

      a_dsig = self._alpha(te, self._d_cutoff)
      dsig = (signal - self._sig) / te
      dsig_hat = self._alpha_blend(a_dsig, dsig, self._dsig)

      cutoff = self._m_cutoff + self._beta * math.fabs(dsig_hat)
      a_sig = self._alpha(te, cutoff)
      sig_hat = self._alpha_blend(a_sig, signal, self._sig)

      self._sig = sig_hat
      self._dsig = dsig_hat
      self._time = timestamp

    else:
      self._sig = signal
      self._dsig = 0.0
      self._time = timestamp

    return self._sig

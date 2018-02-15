"""
replace.py
~~~~~~~~~~

Utilities to aid with building new datasets
"""

import hashlib as _hashlib
import numpy as _np
import datetime as _datetime

import logging as _logging
_logger = _logging.getLogger(__name__)

class AssignNew():
    """An iterable which processes data, together with hashing functions to
    check replicability.  Abstract base class: override :meth:`adjust`.

    :param generator: The input iterator.
    :param seed: If not `None` set the `numpy` random seed to this.
    """
    def __init__(self, generator, seed=None):
        if seed is not None:
            _np.random.seed(seed)
        self._in_msg = _hashlib.sha256()
        self._out_msg = _hashlib.sha256()
        self._gen = generator
        self._null_count = 0
        self._total_count = 0

    @property
    def input_hash(self):
        """The SHA256 hash of all the input rows."""
        return self._in_msg.hexdigest()

    @property
    def output_hash(self):
        """The SHA256 hash of all the output rows."""
        return self._out_msg.hexdigest()

    @property
    def failed_to_reassign_count(self):
        return self._null_count
    
    @property
    def input_size(self):
        return self._total_count

    def __iter__(self):
        old_time = _datetime.datetime.now()
        for row in self._gen:
            self._total_count += 1
            self._in_msg.update(str(row).encode())
            out_row = self.adjust(row)
            if out_row is None:
                self._null_count += 1
                continue
            self._out_msg.update(str(out_row).encode())
            now = _datetime.datetime.now()
            if now - old_time > _datetime.timedelta(minutes=1):
                old_time = now
                _logger.debug("Perfoming new assignment; completed %s rows", self._total_count)
            yield out_row

    def adjust(self, row):
        """Abstract method to override.
        
        :return: New `Row` object, or `None` to indicate that we could not
          sensibly deal with the input.
        """
        raise NotImplementedError()
    
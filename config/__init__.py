"""
MediPOS — Point-of-Sale for a Medicine/Pharmacy Shop.
"""
import sys

if sys.version_info >= (3, 14):
    from copy import copy
    from django.template.context import BaseContext

    def _basecontext_copy(self):
        duplicate = type(self).__new__(type(self))
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = _basecontext_copy

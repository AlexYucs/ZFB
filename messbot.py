import json
import logging
import os
import sys
import time

from dfrotz import DFrotz
import models
import parser


if __name__ == '__main__':
  with open('config.json', 'r') as f:
    config = json.load(f)

import json
import logging
import os
import sys
import time

import redis

from dfrotz import DFrotz
import models
import parser


if __name__ == '__main__':
  with open('config.json', 'r') as f:
    config = json.load(f)
    
  api_key = config['api_key']
  logging.info('Logging in with api key %r.' % api_key)
  
  if len(sys.argv) > 1:
      logging.info('Broadcasting is available! Send /broadcast.')
  for story in config['stories']:
      models.Story(
          name=story['name'],
          abbrev=story['abbrev'],
          filename=story['filename']
      )
      
      
  z5bot = models.Z5Bot.get_instance_or_create()

  p = parser.Parser()
  p.add_default(cmd_default)
  p.add_command('/start', cmd_start)
  p.add_command('/select', cmd_select)
  p.add_command('/load', cmd_load)
  p.add_command('/clear', cmd_clear)
  p.add_command('/enter', cmd_enter)
  p.add_command('/broadcast', cmd_broadcast)
  p.add_command('/i', cmd_ignore)
  p.add_command('/ping', cmd_ping)
  z5bot.add_parser(p)
  
   r = redis.StrictRedis(
      host=config['redis']['host'],
      port=config['redis']['port'],
      db=config['redis']['db'],
      password=config['redis']['password'],
  )
  z5bot.add_redis(r)

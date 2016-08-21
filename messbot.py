from flask import Flask, request
import json
import logging
import os
import sys
import time
import requests

import redis

from dfrotz import DFrotz
import models
import parser

app = Flask(__name__)

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

# This needs to be filled with the Page Access Token that will be provided
# by the Facebook App that will be created.
PAT = str(os.environ.get('FBKey',3))

#verify
@app.route('/', methods=['GET'])
def handle_verification():
  print "Handling Verification."
  if request.args.get('hub.verify_token', '') == 'my_voice_is_my_password_verify_me':
    print "Verification successful!"
    return request.args.get('hub.challenge', '')
  else:
    print "Verification failed!"
    return 'Error, wrong validation token'



#messaging
@app.route('/', methods=['POST'])
def handle_messages():
    print "Handling Messages"
    payload = request.get_data()
    with open('config.json', 'r') as f:
      config = json.load(f)
    

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
  
    #r = redis.StrictRedis(
    #    host=config['redis']['host'],
    #    port=config['redis']['port'],
    #    db=config['redis']['db'],
    #    password=config['redis']['password'],
    #)
    #z5bot.add_redis(r)
    for sender, message in messaging_events(payload):
      if type(message) is not None:
        func = z5bot.parser.get_function(message)
        chat = models.Chat.get_instance_or_create(int(sender))
        func(sender, message, z5bot, chat)
        
    return "ok"
  
#Sorts messages
def messaging_events(payload):
  """Generate tuples of (sender_id, message_text) from the
  provided payload.
  """
  data = json.loads(payload)
  messaging_events = data["entry"][0]["messaging"]
  for event in messaging_events:
    if "message" in event and "text" in event["message"]:
      yield event["sender"]["id"], event["message"]["text"].encode('unicode_escape')
    else:
      yield event["sender"]["id"], "I can't echo this"


#Send the message. Limited to 320 char
def sendMessage(recipient, text):
  """Send the message text to recipient with id recipient.
  """

  r = requests.post("https://graph.facebook.com/v2.6/me/messages",
    params={"access_token": PAT},
    data=json.dumps({
      "recipient": {"id": recipient},
      "message": {"text": text.decode('unicode_escape')}
    }),
    headers={'Content-type': 'application/json'})
  if r.status_code != requests.codes.ok:
    print r.text



def cmd_default(sender, message, z5bot, chat):
    # gameplay messages will be sent here
    if message.strip().lower() == 'load':
        text = 'Please use /load.'
        return sendMessage(sender, text)

    if message.strip().lower() == 'save':
        text = 'Your progress is being saved automatically. But /load is available.'
        return sendMessage(sender, text)

    if not chat.has_story():
        text = 'Please use the /select command to select a game.'
        return sendMessage(sender, text)
    print("BEFORE PROCESS")
    # here, stuff is sent to the interpreter
    #z5bot.redis.rpush('%d:%s' % (sender, chat.story.abbrev), message)
    z5bot.process(int(sender), message)
    print("AFTER PROCESS")
    received = z5bot.receive(int(sender))
    print("recieved "+str(received))
    print("recieved type "+type(received))
    reply = sendMessage(sender, str(received))
    print("AFTER RECIEVED")
    if ' return ' in received.lower() or ' enter ' in received.lower():
        notice = '(Note: You are able to do use the return key by typing /enter.)'
        return sendMessage(sender, notice)

def cmd_start(sender, message, *args):
    text =  'Welcome!\n' 
    text += 'Please use the /select command to select a game.\n'
    return sendMessage(sender, text)

def cmd_select(sender, message, z5bot, chat):
    selection = 'For "%s", write /select %s.'
    msg_parts = []
    for story in models.Story.instances:
        part = selection % (story.name, story.abbrev)
        msg_parts.append(part)
    text = '\n'.join(msg_parts)

    for story in models.Story.instances:
        if ' ' in message and message.strip().lower().split(' ')[1] == story.abbrev:
            chat.set_story(models.Story.get_instance_by_abbrev(story.abbrev))
            z5bot.add_chat(chat)
            reply = sendMessage(sender, 'Starting "%s"...' % story.name)
            
            notice  = 'Your progress will be saved automatically.'
            reply = sendMessage(sender, notice)
            
            reply = sendMessage(sender, z5bot.receive(int(sender)))
            
            #if z5bot.redis.exists('%d:%s' % (int(sender), chat.story.abbrev)):
            #    notice  = 'Some progress in %s already exists. Use /load to restore it ' % (chat.story.name)
            #    notice += 'or /clear to reset your recorded actions.'
            #    reply = sendMessage(sender, notice)
                
            return

    return sendMessage(sender, text)

def cmd_load(sender, message, z5bot, chat):
    if not chat.has_story():
        text = 'You have to select a game first.'
        return sendMessage(sender, text)
        
    #if not z5bot.redis.exists('%d:%s' % (sender, chat.story.abbrev)):
    #    text = 'There is no progress to load.'
    #    return sendMessage(sender, text)

    #text = 'Restoring %d messages. Please wait.' % z5bot.redis.llen('%d:%s' % (sender, chat.story.abbrev))
    #reply = sendMessage(sender, text)
    

    #saved_messages = z5bot.redis.lrange('%d:%s' % (sender, chat.story.abbrev), 0, -1)

    for index, db_message in enumerate(saved_messages):
        z5bot.process(int(sender), db_message.decode('utf-8'))
        if index == len(saved_messages)-2:
            z5bot.receive(int(sender)) # clear buffer
    reply = sendMessage(sender, 'Done.')
    
    return sendMessage(sender, z5bot.receive(int(sender)))


def cmd_clear(sender, message, z5bot, chat):
    #if not z5bot.redis.exists('%d:%s' % (sender, chat.story.abbrev)):
    #    text = 'There is no progress to clear.'
    #    return sendMessage(sender, text)

    #text = 'Deleting %d messages. Please wait.' % z5bot.redis.llen('%d:%s' % (sender, chat.story.abbrev))
    #reply = sendMessage(sender, text)
    

    #z5bot.redis.delete('%d:%s' % (sender, chat.story.abbrev))
    return sendMessage(sender, 'Done.')

def cmd_enter(sender, message, z5bot, chat):
    if not chat.has_story():
        return

    command = '' # \r\n is automatically added by the Frotz abstraction layer
    #z5bot.redis.rpush('%d:%s' % (sender, chat.story.abbrev), command)
    z5bot.process(int(sender), command)
    return sendMessage(sender, z5bot.receive(int(sender)))

def cmd_broadcast(sender, message, z5bot, *args):
    if z5bot.broadcasted or len(sys.argv) <= 1:
        return
    return
    #print(z5bot.redis.keys())
    #active_chats = [int(chat_id.decode('utf-8').split(':')[0]) for chat_id in z5bot.redis.keys()]
    #logging.info('Broadcasting to %d chats.' % len(active_chats))
    #with open(sys.argv[1], 'r') as f:
    #    notice = f.read()
    #for chat_id in active_chats:
    #    logging.info('Notifying %d...' % chat_id)
    #    try:
    #        sendMessage(chat_id, notice)
    #    except:
     #       continue
    #    time.sleep(2) # cooldown
    #z5bot.broadcasted = True

def cmd_ignore(*args):
    return

def cmd_ping(sender, message, *args):
    return sendMessage(sender, 'Pong!')


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
  
  #r = redis.StrictRedis(
  #    host=config['redis']['host'],
  #    port=config['redis']['port'],
  #    db=config['redis']['db'],
  #    password=config['redis']['password'],
  #)
  #z5bot.add_redis(r)
  
  app.run(threaded=True)

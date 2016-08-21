from flask import Flask, request
import json
import logging
import os
import sys
import time
import requests

import textPlayer as tp

app = Flask(__name__)

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

t = tp.TextPlayer('zork1.z5')
start_info = t.run()

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
  for sender, message in messaging_events(payload):
    if message is 'hi':
      sendMessage(sender, start_info)
    else:
      reply = t.execute_command(message)
      sendMessage(sender, reply)
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

def sendMessage(sender, message):
  text = message.splitlines()
  for line in text:
    if len(line)>0:
      while( len(line) > 300):
        msg1 = line[:300]
        line = line[300:]
        send_message(sender, msg1)
      send_message(sender, line)


#Send the message. Limited to 320 char
def send_message(recipient, text):
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


if __name__ == '__main__':
  app.run()


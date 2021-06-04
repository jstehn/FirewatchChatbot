# source code from https://tutorials.botsfloor.com/using-ngrok-for-testing-your-messenger-bot-22a84f8185fb
from sklearn.base import TransformerMixin
import json
import requests
from bottle import debug, request, route, run
import pandas as pd
import numpy as np
import spacy
import pickle
import os
# May need to run beforehand: python -m spacy download en_core_web_md

BOT_RESPONSES = pd.read_json(r'data/responses.json')
NLP = spacy.load('data/en_core_web_md')
GRAPH_URL = "https://graph.facebook.com/v10.0"
VERIFY_TOKEN = 'DR54375234'
PAGE_TOKEN = 'EAAFKXWyhAmIBAA9wMX1QiX2HHePXugS9WTHOp64HEIcgUZB961tzt30kWOkqZB0akInLOIPLZAunbGJDSyjXMNACDbewSukRgEkp3Wcz0u4ncD4d1yXaCnZASjCltBynVqZBsd2ByH6DWmgfmLAxF04cU1nF6CCLDjk1Pt0i824gUyUuGCXWt'


class TextVectorizer(TransformerMixin):
    def transform(self, X, **transform_params):
        new_X = np.zeros((len(X), NLP.vocab.vectors_length))
        # Iterate over the sentences
        for idx, sentence in enumerate(X):
            # Pass each sentence to the NLP object to create a document
            doc = NLP(sentence)
            # Save the document's .vector attribute to the corresponding row in
            # X
            new_X[idx, :] = doc.vector
        return new_X
    def fit(self, X, y=None, **fit_params):
        return self

with open(r'data/model.sav', 'rb') as file:
    MODEL = pickle.load(file)


def find_response(user_message):
    if user_message in BOT_RESPONSES.index:
        return [BOT_RESPONSES["Response"][user_message], BOT_RESPONSES["Links"][user_message]]
    else:
        # return [BOT_RESPONSES["Response"][MODEL.predict([user_message])[0]],df["Links"][MODEL.predict([user_message])[0]]]
        return ["Sorry, I don't understand: " + user_message, ["Help"]]


def send_to_messenger(ctx):
    url = "{0}/me/messages?access_token={1}".format(GRAPH_URL, PAGE_TOKEN)
    response = requests.post(url, json=ctx)


@route('/', method=["GET", "POST"])
def bot_endpoint():
    if request.method.lower() == 'get':
        verify_token = request.GET.get('hub.verify_token')
        hub_challenge = request.GET.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            url = "{0}/me/subscribed_apps?access_token={1}".format(
                GRAPH_URL, PAGE_TOKEN)
            response = requests.post(url)
            return hub_challenge
    else:
        # Receive the message and update the status to be typing
        body = json.loads(request.body.read())
        user_id = body['entry'][0]['messaging'][0]['sender']['id']
        page_id = body['entry'][0]['id']
        ctx = {
            "recipient": {
                "id": user_id,
            },
            "sender_action": "mark_seen"
        }
        response = send_to_messenger(ctx)
        # Get contents of the recieved request
        if 'message' not in body['entry'][0]['messaging'][0]:
            # Webhook that it has received is not a message. Return to avoid a 500 error.
            return ''
        message_text = body['entry'][0]['messaging'][0]['message']['text']
        if user_id != page_id:            
            ctx = {
                "recipient": {
                    "id": user_id,
                },
                "sender_action": "typing_on"
            }
            response = send_to_messenger(ctx)
            message_contents = find_response(message_text)
            ctx = {
                'recipient': {"id": user_id, },
                'message': {
                    "text": message_contents[0],
                    "quick_replies": [{"content_type": "text", "title": item, "payload": "<POSTBACK_PAYLOAD>"} for item in message_contents[1]]
                }
            }
            response = send_to_messenger(ctx)
            ctx = {
                "recipient": {
                    "id": user_id,
                    },
                    "sender_action": "typing_off"
                }
            response = send_to_messenger(ctx)
        return ''


debug(True)
run(host='0.0.0.0', reloader=True, port=os.environ.get('PORT', '5000'))

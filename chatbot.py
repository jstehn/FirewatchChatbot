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
GRAPH_URL = "https://graph.facebook.com/v10.0"
VERIFY_TOKEN, PAGE_TOKEN = os.environ['VERIFY_TOKEN'], os.environ['PAGE_TOKEN']
NLP = spacy.load('data/en_core_web_md')

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

def find_response(user_message):
    if user_message in BOT_RESPONSES.index:
        return [BOT_RESPONSES["Response"][user_message], BOT_RESPONSES["Links"][user_message]]
    else:
        with open(r'data/model.sav', 'rb') as file:
            MODEL = pickle.load(file)
        probabilities = MODEL.predict_proba([user_message])[0]
        max_proba = max(probabilities)
        category = MODEL.classes_[np.argmax(probabilities)]
        if max_proba < 0.6:
            message = "I'm sorry, I don't understand. Let's try something else. What category is your question?"
            links = MODEL.classes_
        else:
            message = BOT_RESPONSES["Response"][category]
            links = BOT_RESPONSES["Links"][category]
        print(f"Predicted Category: {category}, {max_proba}")
        return [message, links]


def send_to_messenger(ctx):
    url = "{0}/me/messages?access_token={1}".format(GRAPH_URL, PAGE_TOKEN)
    print("Sending CTX to url:", ctx)
    response = requests.post(url, json=ctx)
    if response.status_code != 200:
        print("Response Error:", response.text)


@route('/', method=["GET", "POST"])
def bot_endpoint():
    if request.method.lower() == 'get':
        print("Request is a get request (used for verifying).")
        verify_token = request.GET.get('hub.verify_token')
        hub_challenge = request.GET.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            url = "{0}/me/subscribed_apps?access_token={1}".format(
                GRAPH_URL, PAGE_TOKEN)
            response = requests.post(url)
            print("Hub challenge:", hub_challenge)
            return hub_challenge
    else:
        # Receive the message and update the status to be typing
        body = json.loads(request.body.read())
        print("Message received:", body)
        user_id = body['entry'][0]['messaging'][0]['sender']['id']
        page_id = body['entry'][0]['id']
        ctx = {
            "recipient": {
                "id": user_id,
            },
            "sender_action": "mark_seen"
        }
        send_to_messenger(ctx)
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
            send_to_messenger(ctx)
            message_contents = find_response(message_text)
            # Cases that we care about:
            # 1) It's a wit$greetings
            # 2) It's wit$bye
            fb_nlp = body['entry'][0]['messaging'][0]['message']['nlp']['traits']
            if "wit$greetings" in fb_nlp:
                if fb_nlp["wit$greetings"]["value"] == "true" and fb_nlp["wit$greetings"]["confidence"] >= 0.95:
                    message_contents = ["Hello, there!",["Help"]]
            if "wit$bye" in fb_nlp:
                if fb_nlp["wit$bye"]["value"] == "true" and fb_nlp["wit$bye"]["confidence"] >= 0.95:
                    message_contents = ["Goodbye!",["Help"]]
            if "wit$thanks" in fb_nlp:
                if fb_nlp["wit$thanks"]["value"] == "true" and fb_nlp["wit$thanks"]["confidence"] >= 0.95:
                    message_contents = ["You're welcome!",["Help"]]   
            ctx = {
                "recipient": {
                    "id": user_id,
                },
                "message": {
                    "text": message_contents[0],
                    "quick_replies":
                    [
                        {"content_type": "text", "title": item,
                         "payload": "<POSTBACK_PAYLOAD>"}
                        for item in message_contents[1]
                    ]
                }
            }
            send_to_messenger(ctx)
            ctx = {
                "recipient": {
                    "id": user_id,
                },
                "sender_action": "typing_off"
            }
            send_to_messenger(ctx)
        return ''


debug(True)
run(host='0.0.0.0', reloader=True, port=os.environ.get('PORT', '5000'))

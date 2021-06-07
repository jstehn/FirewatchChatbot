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
    fb_nlp = user_message['nlp']['traits']
    nlp_proba = {}
    print("Facebook's NLP:", fb_nlp)
    for trait in ("greetings", "bye", "thanks"):
        if f"wit${trait}" in fb_nlp:
            if fb_nlp[f"wit${trait}"][0]["value"] == "true":
                print(trait, fb_nlp[f"wit${trait}"][0]["confidence"])
                nlp_proba[trait] = fb_nlp[f"wit${trait}"][0]["confidence"]
            else:
                nlp_proba[trait] = 0
        else:
            nlp_proba[trait] = 0
    probable_trait = max(nlp_proba, key=nlp_proba.get)
    if nlp_proba[probable_trait] >= 0.95:
        print(
            f"Facebook classification: {probable_trait}, {nlp_proba[probable_trait]}")
        message_text = probable_trait
    else:
        message_text = user_message["text"]

    if message_text in BOT_RESPONSES.index:
        message = BOT_RESPONSES["Response"][message_text]
        links = BOT_RESPONSES["Links"][message_text]
    else:
        with open(r'data/model.sav', 'rb') as file:
            MODEL = pickle.load(file)
        probabilities = MODEL.predict_proba([message_text])[0]
        max_proba = max(probabilities)
        category = MODEL.classes_[np.argmax(probabilities)]
        if max_proba < 0.6:
            message = "I'm sorry, I don't understand. Let's try something else. What category is your question?"
            links = MODEL.classes_
        else:
            message = BOT_RESPONSES["Response"][category]
            links = BOT_RESPONSES["Links"][category]
        print(f"Predicted Category: {category}, {max_proba}")    
    return {"message": message, "quick_responses": links}


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
        user_message = body['entry'][0]['messaging'][0]['message']
        if user_id != page_id:
            ctx = {
                "recipient": {
                    "id": user_id,
                },
                "sender_action": "typing_on"
            }
            send_to_messenger(ctx)
            message_contents = find_response(user_message)
            print(message_contents)
            split_message = user_message["message"].split("\n\n")
            for i in range(len(split_message)):
                ctx = {
                    "recipient": {
                        "id": user_id,
                    },
                    "message": {
                        "text": split_message[i],
                    }
                }
                if i == (len(split_message) - 1):
                    ctx["message"]["quick_replies"] = [
                        {"content_type": "text", "title": item,
                         "payload": "<POSTBACK_PAYLOAD>"}
                        for item in message_contents["quick_responses"]
                    ]
                send_to_messenger(ctx)

            ctx = {
                "recipient": {
                    "id": user_id,
                },
                "message": {
                    "text": message_contents["message"],
                    "quick_replies":
                    [
                        {"content_type": "text", "title": item,
                         "payload": "<POSTBACK_PAYLOAD>"}
                        for item in message_contents["quick_responses"]
                    ]
                }
            }
            
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

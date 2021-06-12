from sklearn.base import TransformerMixin
import json
import requests
from bottle import debug, request, route, run
import pandas as pd
import numpy as np
import spacy
import pickle
import os
from collections import deque

# May need to run beforehand: python -m spacy download en_core_web_md

BOT_RESPONSES = pd.read_json(r"data/responses.json")
GRAPH_URL = "https://graph.facebook.com/v10.0"
VERIFY_TOKEN, PAGE_TOKEN = os.environ["VERIFY_TOKEN"], os.environ["PAGE_TOKEN"]
NLP = spacy.load("en_core_web_md")
recent_messages = deque(maxlen=255)


class TextVectorizer(TransformerMixin):
    """Text Vectorizer for intent classification model"""
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


class FacebookChat:
    """
    A class to organize correspondence with a particular user.

    Attributes
    ----------
    userid : str
        User ID that these messages will be sent to.

    url : str
        API url

    Methods
    -------

    """

    def __init__(self, userid):
        self.__userid = userid
        self.__url = "{0}/me/messages?access_token={1}".format(GRAPH_URL, PAGE_TOKEN)

    def send_to_messenger(self, ctx):
        """Sends the request to API at the recipient ID

        Args:
            ctx (dict) : Dictionary following Facebooks API to send content over messenger

        Returns:
            response : Response variable of the request
        """
        ctx["recipient"] = {"id": self.__userid}
        response = requests.post(self.__url, json=ctx)
        if response.status_code != 200:
            print("Response Error:", response.text)
        return response

    def read(self):
        """Marks the chat as read"""
        ctx = {
            "sender_action": "mark_seen",
        }
        return self.send_to_messenger(ctx)

    def typing(self, on):
        """Updates so that the chat appears to be typing or not typing

        Args:
            on (bool): Indicates if the bot is typing or not

        Returns:
            Response: Response object
        """
        if on:
            ctx = {
                "sender_action": "typing_on",
            }
        else:
            ctx = {
                "sender_action": "typing_off",
            }
        return self.send_to_messenger(ctx)

    def message(self, contents):
        """
        Sends message with quick replies

        Paramters:
            contents (dict) : First element is a string to be sent as a message. Second element is a list of strings for quick replies
        """
        split_message = contents["message"].split("\n\n")
        for i in range(len(split_message)):
            ctx = {
                "message": {
                    "text": split_message[i],
                },
            }
            if i == (len(split_message) - 1):
                ctx["message"]["quick_replies"] = [
                    {
                        "content_type": "text",
                        "title": item,
                        "payload": "<POSTBACK_PAYLOAD>",
                    }
                    for item in contents["quick_responses"]
                ]
            self.send_to_messenger(ctx)


def find_response(user_message):
    """Finds the best response to a user's message:
    1)  Tries to see if the message is a greeting, goodbye, or thanks.
    2)  Checks to see if the message is an exact string match to something we
        already have a response to
    3)  If there is no match, try to figure out user intent and use that to
        find a proper response.

    Args:
        user_message (string): Message that user sent

    Returns:
        dict:   Dictionary with value of "messsage" as a string and value of
                "quick_responses" as a list of strings that are used as
                quick responses.
    """

    fb_nlp = user_message["nlp"]["traits"]
    nlp_proba = {}
    for trait in ("greetings", "bye", "thanks"):
        if f"wit${trait}" in fb_nlp:
            if fb_nlp[f"wit${trait}"][0]["value"] == "true":
                nlp_proba[trait] = fb_nlp[f"wit${trait}"][0]["confidence"]
            else:
                nlp_proba[trait] = 0
        else:
            nlp_proba[trait] = 0
    probable_trait = max(nlp_proba, key=nlp_proba.get)
    if nlp_proba[probable_trait] >= 0.90:
        print(f"Facebook classification: {probable_trait}, {nlp_proba[probable_trait]}")
        message_text = probable_trait
    else:
        message_text = user_message["text"]

    if message_text in BOT_RESPONSES.index:
        message = BOT_RESPONSES["Response"][message_text]
        links = BOT_RESPONSES["Links"][message_text]
    else:
        with open("data/model.sav", "rb") as file:
            MODEL = pickle.load(file)
        probabilities = MODEL.predict_proba([message_text])[0]
        max_proba = max(probabilities)
        category = MODEL.classes_[np.argmax(probabilities)]
        if max_proba < 0.6:
            message = "I'm sorry, I don't understand. Let's try something else. What category is your question?"
            print("Predicted Category: Unknown")
            links = MODEL.classes_
        else:
            message = BOT_RESPONSES["Response"][category]
            links = BOT_RESPONSES["Links"][category]
            print(f"Predicted Category: {category}, {max_proba}")
    print("Bot response: {}".format(message.replace("\n", " ")))
    return {"message": message, "quick_responses": links}


@route("/", method=["GET", "POST"])
def bot_endpoint():
    if request.method.lower() == "get":
        print("Request is a get request (used for verifying).")
        verify_token = request.GET.get("hub.verify_token")
        hub_challenge = request.GET.get("hub.challenge")
        if verify_token == VERIFY_TOKEN:
            url = "{GRAPH_URL}/me/subscribed_apps?access_token={PAGE_TOKEN}"
            response = requests.post(url)
            print("Hub challenge:", hub_challenge)
            return hub_challenge
    else:
        body = json.loads(request.body.read())
        user_id = body["entry"][0]["messaging"][0]["sender"]["id"]
        page_id = body["entry"][0]["id"]
        user_message = body["entry"][0]["messaging"][0]["message"]
        message_id = user_message["mid"]
        print(f'Message ID "{message_id}" received.')
        if message_id in recent_messages:
            print(f"Already responded; ignoring messaged.")
            return ""
        recent_messages.append(message_id)
        if user_id != page_id:
            chat = FacebookChat(user_id)
            chat.read()
            chat.typing(True)
            message_contents = find_response(user_message)
            chat.message(message_contents)
        return ""


run(host="0.0.0.0", reloader=True, port=os.environ.get("PORT", "5000"))

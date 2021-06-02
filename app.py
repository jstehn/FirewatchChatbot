#source code from https://tutorials.botsfloor.com/using-ngrok-for-testing-your-messenger-bot-22a84f8185fb
import json
import requests
import pandas as pd
from bottle import debug, request, route, run
import pandas as pd
import numpy as np
import spacy
import pickle

#colab 1
df = pd.read_json('responses.json')
#df = pd.read_csv("BotResponsesSheet1.csv")
#df = df.iloc[1:]
#df = df.set_index("Key").fillna("")
# This just straight up evaluates the cell. Vulnerable to attacks in other applications but it's a nice fix for what we need. Just need to make sure the cell looks exactly like a list.
# Honestly, the better action is probably just making a seperating character like ; and using the split method. Just need to make sure the character is ONLY used for splitting.
#df["Links"] = df["Links"].apply(lambda x: x.split(";") if x else [])

from sklearn.base import TransformerMixin
class TextVectorizer(TransformerMixin):
  def transform(self, X, **transform_params):
    nlp = spacy.load('en_core_web_lg')
    new_X = np.zeros((len(X), nlp.vocab.vectors_length))
    # Iterate over the sentences
    for idx, sentence in enumerate(X):
        # Pass each sentence to the nlp object to create a document
        doc = nlp(sentence)
        # Save the document's .vector attribute to the corresponding row in     
        # X
        new_X[idx, :] = doc.vector
    return new_X
  def fit(self, X, y=None, **fit_params):
    return self

#model 
def find_response(user_message):
  if user_message in df.index:
    return [df["Response"][user_message],df["Links"][user_message]]
    #return df["Links"][user_message]

    # send df.loc["message"]["Response"] and a button for each item in df.loc["message"]["Links"]
  else:
    filename = 'finalized_model.sav'
    #with open(filename, 'rb') as file:
    #    loaded_model = pickle.load(file)
    #return [df["Response"][loaded_model.predict([user_message])[0]],df["Links"][loaded_model.predict([user_message])[0]]]
    return ["sorry I don't understand: " + user_message, ["Help"]]
    # run classification algorithm and choose a response based on that.

GRAPH_URL = "https://graph.facebook.com/v10.0"
VERIFY_TOKEN = 'DR54375234'
PAGE_TOKEN = 'EAAFKXWyhAmIBAA9wMX1QiX2HHePXugS9WTHOp64HEIcgUZB961tzt30kWOkqZB0akInLOIPLZAunbGJDSyjXMNACDbewSukRgEkp3Wcz0u4ncD4d1yXaCnZASjCltBynVqZBsd2ByH6DWmgfmLAxF04cU1nF6CCLDjk1Pt0i824gUyUuGCXWt'




def send_to_messenger(ctx):
    url = "{0}/me/messages?access_token={1}".format(GRAPH_URL, PAGE_TOKEN)
    response = requests.post(url, json=ctx)

@route('/chat', method=["GET", "POST"])
def bot_endpoint():
    if request.method.lower() == 'get':
        verify_token = request.GET.get('hub.verify_token')
        hub_challenge = request.GET.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            url = "{0}/me/subscribed_apps?access_token={1}".format(GRAPH_URL, PAGE_TOKEN)
            response = requests.post(url)
            return hub_challenge
    else:
        body = json.loads(request.body.read())
        with open('data.txt', 'w') as outfile:
            json.dump(body, outfile)
        user_id = body['entry'][0]['messaging'][0]['sender']['id']
        page_id = body['entry'][0]['id']
        #message_id = body[]
        #url = "{0}/{1}?access_token={2}".format(GRAPH_URL, page_id, PAGE_TOKEN)
        #message_body = requests.get(url)
        #with open('data1.txt', 'w') as outfile:
        #    outfile.write(message_body.text)
        message_text = body['entry'][0]['messaging'][0]['message']['text']
        # we just echo to show it works
        # use your imagination afterwards
        if user_id != page_id:
            
            ctx = {
                'recipient':{"id":user_id,},
                'message':{
                    "text": find_response(message_text)[0],
                    "quick_replies":[{"content_type":"text", "title":item, "payload":"<POSTBACK_PAYLOAD>"} for item in find_response(message_text)[1]]
                }
            }
            #find_response(message_text)
            response = send_to_messenger(ctx)
        return ''


debug(True)
run(reloader=True, port=5000)
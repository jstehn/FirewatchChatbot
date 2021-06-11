Table of Contents
- [FirewatchChatbot](#firewatchchatbot)
- [Methodology](#methodology)
  - [Intent Classification Model](#intent-classification-model)
  - [Data](#data)
  - [Platform](#platform)

# FirewatchChatbot

A Facebook chatbot done as a DataGood project for CalSAFE. The goal is to create a chatbot that can identify the kind of question about wildfires that the user is asking and provide helpful responses. This bot's emphasis is primarily California wildfires. 

# Methodology

A model was created using Natural Language Processing (NLP) to perform Intent Classification. This classification is used on incoming messages to the bot and helps guides the bot's responses. This was trained on a small database of questions collected from the Internet by the team. The bot provides a list of related questions and the user can read about the topic.


## Intent Classification Model

While many out-of-the-box chatbots exist, I wanted to build one myself using sklearn and spacy. In short, spacy's web-trained language model is used to vectorize the questions and then classification is run on that 300 dimentional vector. This is demonstrated in `model-creation.ipynb`. Numerous models were created, but ultimately a simple logistic regression ended up being the most accurate and quickest option, leading to a better end user experience.

## Data

The data was collected and classified manually by the team from across the internet. The goal was to get a sample of how people ask questions related to wildfires when chatting on the web. It is not training data that teaches the bot how to formulate a natural human response. We just want to the bot to understand what the user is trying to ask and give a response from a pre-selected list of responses. Quora, reddit, Answers, Facebook, Twitter, and local fire department websites were just some of the places where these questions were collected. The sample had about 450 questions that were classified by the team manually. The categories currently implemented are Fire Preparation, Fire Ecology, Emergency Protocols, Fire Recovery, and Getting Involved. Our hope is to expand this dataset later as it interacts with users.

## Platform

The bot is to be hosted on Heroku using Flask. It connects using Facebook's API. It uses the incoming messages, runs intent classification, and gives users options based on what it perceived the user's intent to be.

Partially inspired by: https://tutorials.botsfloor.com/using-ngrok-for-testing-your-messenger-bot-22a84f8185fb
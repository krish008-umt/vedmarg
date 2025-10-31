# vedmarg
AI powered Mental Health Assistant Chatbot

How It Works

The user enters text, records audio, or uploads video.

The system detects emotion using:

A custom-trained text emotion model

OpenSMILE for voice tone analysis

DeepFace for facial emotion recognition

The detected emotions and interaction history are stored in the database.

A RAG (Retrieval Augmented Generation) system retrieves relevant mental-health guidance from our knowledge base.

This information is passed to the Gemini API, which generates a personalized, empathetic response.

The dashboard shows mood patterns over time and gives wellness suggestions in interactive format.


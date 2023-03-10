import slack
import os
from flask import Flask, request, json, Response
from dotenv import load_dotenv
from slackeventsapi import SlackEventAdapter
from User_Story_Analysis.getprediction import prediction

load_dotenv()

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

us_analysis = {}
word_categories = {}
user_story = ""


@slack_event_adapter.on('message')
def message(payload):
    print(payload)
    event = payload.get('event', {})
    channel_id = event.get('channel')

    if event.get('bot_id') == os.environ['TRELLO_ID']:
        global user_story
        user_story = event.get('attachments')[0]['title']
        global us_analysis, word_categories
        us_analysis, word_categories = prediction(user_story)
        if us_analysis.item(0) >= 0.5:
            blocks = [{"type": "section",
                       "text": {"type": "plain_text",
                                "text": "User Story from Trello: \n" + user_story}
                       },
                      {
                          "type": "section",
                          "text": {
                              "type": "mrkdwn",
                              "text": "Privacy Content Detected!"
                          },
                      },

                      {
                          "type": "actions",
                          "elements": [
                              {
                                  "type": "button",
                                  "text": {
                                      "type": "plain_text",
                                      "text": "Show Privacy Words",
                                      "emoji": True
                                  },
                                  "value": "privacyword",
                                  "action_id": "action-show"
                              }
                          ]
                      }

                      ]

        else:
            blocks = [{"type": "section",
                       "text": {"type": "plain_text",
                                "text": "User Story on Trello: " + user_story}
                       },
                      {
                          "type": "section",
                          "text": {
                              "type": "mrkdwn",
                              "text": "No Privacy Content Detected!"
                          },
                      }]
        client.chat_postMessage(channel=channel_id, blocks=blocks)


@app.route('/slack/actions', methods=['POST'])
def handle_action():
    data = json.loads(request.form["payload"])
    action = data.get("actions")[0].get("action_id")
    if action == "action-show":
        blocks = [{"type": "section",
                   "text": {"type": "plain_text",
                            "text": "User Story from Trello: \n" + user_story}
                   },
                  {
                      "type": "section",
                      "text": {
                          "type": "mrkdwn",
                          "text": "Privacy Content Detected!"
                      },
                  }
                  ]
        for w in word_categories:
            word = w[0]
            category = w[1]
            description = w[2]
            blocks += [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text":
                        "   • Privacy Word: " + word +
                        "\n • Privacy Category: " + category +
                        "\n • Privacy Description : " + description
                }
            }]
        blocks += [{
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Hide Privacy Words",
                        "emoji": True
                    },
                    "value": "privacyword",
                    "action_id": "action-hide"
                }
            ]
        }]
        client.chat_update(channel=data.get("channel").get("id"), ts=data.get("message").get("ts"), blocks=blocks)

    if action == "action-hide":
        blocks = [{"type": "section",
                   "text": {"type": "plain_text",
                            "text": "User Story from Trello: \n" + user_story}
                   },
                  {
                      "type": "actions",
                      "elements": [
                          {
                              "type": "button",
                              "text": {
                                  "type": "plain_text",
                                  "text": "Show Privacy Words",
                                  "emoji": True
                              },
                              "value": "privacyword",
                              "action_id": "action-show"
                          }
                      ]
                  }
                  ]

        client.chat_update(channel=data.get("channel").get("id"), ts=data.get("message").get("ts"), blocks=blocks)

    return Response(), 200


if __name__ == "__main__":
    app.run(debug=True)

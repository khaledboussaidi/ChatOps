import datetime
import json
import logging
import os
from json import JSONEncoder

import requests
import yaml
from kubernetes import client, config
from utils import HELP, LIST, POD, DEPLOYMENT, SERVICE, LOG, RESTART, DEPLOY, DESCRIBE, SCALE
import auth
import boto3
from flask import Flask,request
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from chatBot import ChatBot

class MyEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.date):
            return dict(year=o.year, month=o.month, day=o.day)
        else:
            return o.__dict__
app = Flask(__name__)

KUBE_FILEPATH = '/tmp/kubeconfig'
REGION = 'eu-west-1'
BOT_TOKEN = '*****************'
K8S_TOKEN="*******************************"
CLUSTER_NAME="vynd-monitoring"
MAX_LOG_LENGTH = 200
SLACK_URL = "https://slack.com/api/chat.postMessage"

SLACK_EVENTS_TOKEN="******"
slack_events_adapter = SlackEventAdapter(SLACK_EVENTS_TOKEN, "/slack/events", app)

SLACK_TOKEN='******'
slack_web_client = WebClient(token=SLACK_TOKEN)


"""create kub config """
if not os.path.exists(KUBE_FILEPATH):
    kube_content = dict()
    # Get data from EKS API
    eks_api = boto3.client('eks', region_name=REGION)
    cluster_info = eks_api.describe_cluster(name=CLUSTER_NAME)
    certificate = cluster_info['cluster']['certificateAuthority']['data']
    endpoint = cluster_info['cluster']['endpoint']

    # Generating kubeconfig
    kube_content = dict()

    kube_content['apiVersion'] = 'v1'
    kube_content['clusters'] = [
        {
            'cluster':
                {
                    'server': endpoint,
                    'certificate-authority-data': certificate
                },
            'name': 'kubernetes'

        }]

    kube_content['contexts'] = [
        {
            'context':
                {
                    'cluster': 'kubernetes',
                    'user': 'aws'
                },
            'name': 'aws'
        }]

    kube_content['current-context'] = 'aws'
    kube_content['Kind'] = 'config'
    kube_content['users'] = [
        {
            'name': 'aws',
            'user': ['lambda']
        }]

    # Write kubeconfig
    with open(KUBE_FILEPATH, 'w') as outfile:
        yaml.dump(kube_content, outfile, default_flow_style=False)

def flip_coin(channel,text):

    coin_bot = ChatBot(channel)

    message = coin_bot.get_message_payload(text)

    slack_web_client.chat_postMessage(**message)



@slack_events_adapter.on("message")
#@app.route('/post',methods=['POST'])
def message(payload):
    #print(request.json)
    #event = payload.get("event", {})
    lambda_handler(payload)
    #return "ok",200
    """"event = payload.get("event", {})

    text = event.get("text")


    if "hey"in text.lower():

        channel_id = event.get("channel")


        return flip_coin(channel_id,str(payload))"""""

"""event function"""




def lambda_handler(payload):
    data = payload

    if "challenge" in data:
        return {
            'statusCode': 200,
            'body': json.dumps(data['challenge'])
        }

    slack_event = data.get("event", {})
    channel_id = slack_event.get("channel")

    print(slack_event)

    if "bot_id" in slack_event:
        logging.warn("Ignore bot event")
        return
    else:
        text = slack_event.get("text")

        tokens = cleanInput(text).split()
        action = tokens[0]
        print("********************************************")
        print(action)
        print("********************************************")

        if action.upper() in HELP:
            return sendHelpMessage(channel_id, True)

        v1, v1_beta,app_v1, v1_beta2 = k8s_configuration()

        if action.upper() in LIST:
            if len(tokens) > 1:
                element = tokens[1]
                if element.upper() in POD:
                    # Get all the pods
                    ret = v1.list_namespaced_pod("default")
                    return sendListOfPods(channel_id, ret.items)

                if element.upper() in DEPLOYMENT:
                    # Get all the pods
                    ret = v1_beta.list_namespaced_deployment("default")
                    return sendListOfDeployements(channel_id, ret.items)

                if element.upper() in SERVICE:
                    # Get all the pods
                    ret = v1.list_namespaced_service("default")
                    return sendListOfServices(channel_id, ret.items)

        if action.upper() in LOG:
            if len(tokens) > 1:
                pod_id = tokens[1]
                response = v1.read_namespaced_pod_log(pod_id, 'default')
                print(len(response))
                return sendLogsOfPod(channel_id, response[:int(MAX_LOG_LENGTH)])
        if action.upper() in RESTART:
            if len(tokens) > 1:
                dep_id = tokens[1]
                ret = v1_beta.list_namespaced_deployment("default")
                pod_list = v1.list_namespaced_pod("default")
                couter=0
                for deployment in ret.items:
                    if dep_id==deployment.metadata.name:
                        couter+=1
                        for pod in pod_list.items:
                            if dep_id in pod.metadata.name:
                                response = v1.delete_namespaced_pod(name=pod.metadata.name, namespace='default')
                        return sendDeletedDeployment(channel_id,"Restarted deployment: "+dep_id)
                if couter==0:
                    return sendDeletedDeployment(channel_id, "deployment "+dep_id+ " n'existe pas")
        if action.upper() in DEPLOY:
            if len(tokens) > 1:
                dep_id = tokens[1]
                try:
                    api_response = app_v1.read_namespaced_deployment(dep_id, "default")
                    image = api_response.spec.template.spec.containers[0].image
                    image = image.split(":")
                    if len(image) == 2:
                        image[1] = ""
                        image = "".join(image)

                    else:
                        image.append('')
                        image = "".join(image)
                    body = api_response
                    body.spec.template.spec.containers[0].image = image
                    resp = v1_beta2.patch_namespaced_deployment(
                    name="vynd-chatops",
                    namespace="default",
                    body=body
                    )
                    return sendUpdateddDeploymentImage(channel_id,"Updated deployment image latest ==> "+image)
                except:
                    return sendUpdateddDeploymentImage(channel_id, "deployment "+dep_id+ " n'existe pas")

        if action.upper() in DESCRIBE:
            if len(tokens) > 1:
                dep_id = tokens[1]
                try:
                    api_response = app_v1.read_namespaced_deployment(dep_id, "default")
                    return sedDeploymentDescription(channel_id,ToYaml(api_response.metadata)),sedDeploymentDescription(channel_id,ToYaml(api_response.spec.template.spec)),sedDeploymentDescription(channel_id,ToYaml(api_response.status))
                except:
                    return sedDeploymentDescription(channel_id,"deployment "+dep_id+ " n'existe pas")
        if action.upper() in SCALE:
            if len(tokens) > 2:
                dep_id = tokens[1]
                test=False
                try:
                    scale_num=int(tokens[2])
                    test=True
                except:
                    return sedDeploymentDescription(channel_id, "erruer: vous devez saisir un entier !!!")
                if test:
                    try:
                        api_response = app_v1.read_namespaced_deployment(dep_id, "default")
                        body = api_response
                        body.spec.replicas = scale_num
                        v1_beta2.patch_namespaced_deployment(name=dep_id,namespace="default",body=body)
                        return sedDeploymentDescription(channel_id, "Updated scale for  " + dep_id + " to " + str(scale_num))
                    except:
                        return sedDeploymentDescription(channel_id, "deployment " + dep_id + " n'existe pas")

        return sendHelpMessage(channel_id, False)
"""message type """
def sendHelpMessage(channel_id, indr):
    help_items = [
        "• *list <elements>: * pour afficher la liste des élements de Kubernetes (pods, services, deployments, ...)",
        "• *describe <element> :* pour décrire un élement de Kubernetes",
        "• *logs <pod> :* pour afficher les journaux d'un pod",
        "• *scale <deployement> <replicas> :* pour modifier le nombre des machines d'un deployment",
        "• *deploy <deployement> :* pour déployer la dernière version de l'image Docker d'un deployment",
        "• *restart <deployement> :* pour redémarrer un deployment"
    ]
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                            "" if indr else "J'ai pas compris, ") + "Vous pouvez utiliser l'une des commandes suivantes :\n" + "\n".join(
                    help_items)
            }
        }
    ]

    return sendMessageToSlack(channel_id, "Help" if indr else "Ops", blocks)

def sendDeletedDeployment(channel_id,text):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                            text
                )
            }
        }
    ]


    return sendMessageToSlack(channel_id, "", blocks)

def sendUpdateddDeploymentImage(channel_id, text):
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        text
                    )
                }
            }
        ]
        return sendMessageToSlack(channel_id, "", blocks)
def sedDeploymentDescription(channel_id, result):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "```" + result + "```"
                )
            }
        }
    ]
    return sendMessageToSlack(channel_id, "", blocks)
def sendLogsOfPod(channel_id, log_str):

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "```" + log_str + "```"
            }
        }]

    return sendMessageToSlack(channel_id, "Log pod", blocks)


def sendListOfPods(channel_id, list_items):
    result = ["Etat | Nombre de containers | Namespace | Nom",
              "--------------------------------------------------------------------------------"]
    for i in list_items:
        result.append(
            "%4s | %20s | %9s | %s" % (i.status.phase, len(i.spec.containers), i.metadata.namespace, i.metadata.name))

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Liste des *pods* :"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "```" + "\n".join(result) + "```"
            }
        }]

    return sendMessageToSlack(channel_id, "Liste des pods", blocks)


def sendListOfDeployements(channel_id, list_items):
    result = ["Nombre de pods | Namespace | Nom",
              "--------------------------------------------------------------------------------"]
    for i in list_items:
        result.append(
            "%14s | %9s | %s" % (i.spec.replicas, i.metadata.namespace, i.metadata.name))

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Liste des *depolyments* :"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "```" + "\n".join(result) + "```"
            }
        }]

    return sendMessageToSlack(channel_id, "Liste des deployments", blocks)


def sendListOfServices(channel_id, list_items):
    result = ["%12s | Nom" % "Type",
              "--------------------------------------------------------------------------------"]
    for i in list_items:
        result.append(
            "%12s | %s" % (i.spec.type, i.metadata.name))

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Liste des *services* :"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "```" + "\n".join(result) + "```"
            }
        }]

    return sendMessageToSlack(channel_id, "Liste des services", blocks)


def sendMessageToSlack(channel_id, text, blocks):
    requests.post(SLACK_URL, {
        'token': BOT_TOKEN,
        'channel': channel_id,
        'text': text,
        'blocks': json.dumps(blocks) if blocks else None
    }).json()

    return {
        'statusCode': 200,
        'body': json.dumps(
            'OK'
        )
    }
"""kubernetes confiq and auth"""
def k8s_configuration():
    eks = auth.EKSAuth(cluster_id=CLUSTER_NAME)
    token = eks.get_token()

    # Configure
    config.load_kube_config(KUBE_FILEPATH)
    configuration = client.Configuration()
    configuration.api_key['authorization'] = K8S_TOKEN
    configuration.api_key_prefix['authorization'] = 'Bearer'
    # API
    api = client.ApiClient(configuration)
    v1 = client.CoreV1Api(api)
    v1_beta = client.AppsV1beta1Api(api)
    api_v1=client.AppsV1Api(api)
    v1_beta2 = client.AppsV1beta2Api(api)
    return v1, v1_beta, api_v1, v1_beta2
"""clean text """
def cleanInput(text):
    returned_text = text.replace("mta3 el ", "")
    returned_text = returned_text.replace("mta3 ", "")
    returned_text = returned_text.replace("of the ", "")
    returned_text = returned_text.replace("of  ", "")
    returned_text = returned_text.replace("de  ", "")
    returned_text = returned_text.replace("des  ", "")
    returned_text = returned_text.replace("la  ", "")
    returned_text = returned_text.replace("le  ", "")
    return returned_text

def removeNone(d):
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        if isinstance(value, dict):
            removeNone(value)
        elif isinstance(value, list):
            for dic in value:
                if isinstance(dic, str):
                    pass
                else:removeNone(dic)
    return d
def ToYaml(api_response):
    jsonStr = MyEncoder().encode(api_response)
    jsonStr = removeNone(json.loads(jsonStr))
    jsonStr = json.dumps(jsonStr)
    return str(yaml.safe_dump(yaml.safe_load(jsonStr)))

if __name__ == "__main__":
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)

    logger.addHandler(logging.StreamHandler())


    app.run(host='0.0.0.0', port=8080)
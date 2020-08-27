import os
from kubernetes import client, config

config.load_kube_config(
    os.path.join(os.environ["HOME"], '.kube/config'))

v1 = client.CoreV1Api()

pod_list = v1.list_namespaced_pod("default")
for pod in pod_list.items:
    print("%s\t%s\t%s" % (pod.metadata.name,
                          pod.status.phase,
                          pod.status.pod_ip))
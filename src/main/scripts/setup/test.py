from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from six.moves import input

credentials = GoogleCredentials.get_application_default()
compute = discovery.build('compute', 'v1', credentials=credentials)
email_id="tahir"

# [START list_instances]
def list_instances(compute, project, zone, filt):
    result = compute.instances().list(project=project, zone=zone, filter=filt).execute()
    return result['items']
# [END list_instances]

filt="name eq " + email_id + ".*"
instances = list_instances(compute, "festive-courier-755", "us-central1-f", filt)
print "Name             Status            IP"
for instance in instances:
  if instance["name"].startswith('tahir'):
    print (instance["name"] + "    " + instance["status"] + "    " + instance["machineType"] + "     " + instance["networkInterfaces"][0]["networkIP"] )

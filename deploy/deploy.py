import zipfile
import os
import uuid
import boto3 
import logging
import json
import sys
import botocore
from datetime import datetime

cf = boto3.client('cloudformation')  # pylint: disable=C0103
log = logging.getLogger('deploy.cf.create_or_update')  # pylint: disable=C0103

def updateTemplate(stack_name, template, parameters):
    'Update or create stack'

    template_data = _parse_template(template)
    parameter_data = parameters

    params = {
        'StackName': stack_name,
        'TemplateBody': template_data,
        'Parameters': parameter_data,
    }

    try:
        if _stack_exists(stack_name):
            print('Updating {}'.format(stack_name))
            stack_result = cf.update_stack(**params, Capabilities=['CAPABILITY_IAM'])
            waiter = cf.get_waiter('stack_update_complete')
        else:
            print('Creating {}'.format(stack_name))
            stack_result = cf.create_stack(**params, Capabilities=['CAPABILITY_IAM'])
            waiter = cf.get_waiter('stack_create_complete')
        print("...waiting for stack to be ready...")
        waiter.wait(StackName=stack_name)
    except botocore.exceptions.ClientError as ex:
        error_message = ex.response['Error']['Message']
        if error_message == 'No updates are to be performed.':
            print("No changes")
        else:
            raise
    else:
        print(json.dumps(
            cf.describe_stacks(StackName=stack_result['StackId']),
            indent=2,
            default=json_serial
        ))


def _parse_template(template):
    with open(template) as template_fileobj:
        template_data = template_fileobj.read()
    cf.validate_template(TemplateBody=template_data)
    return template_data


def _parse_parameters(parameters):
    with open(parameters) as parameter_fileobj:
        parameter_data = json.load(parameter_fileobj)
    return parameter_data


def _stack_exists(stack_name):
    stacks = cf.list_stacks()['StackSummaries']
    for stack in stacks:
        if stack['StackStatus'] == 'DELETE_COMPLETE':
            continue
        if stack_name == stack['StackName']:
            return True
    return False


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")



lambdasFolder = "../src/lambdas/"

files = os.listdir(lambdasFolder)


lamdasZipFileName = "lambas_" + str(uuid.uuid4()) + ".zip"

with zipfile.ZipFile(lamdasZipFileName, mode="w") as archive:
    for filename in files:
        archive.write(lambdasFolder + filename, arcname=filename)

client = boto3.client("s3")
client.upload_file(lamdasZipFileName, "zipfileuploaddeploy", "prefix/functions/packages/CleanupPV/"+lamdasZipFileName)



param = [
    {
        "ParameterKey": "QSS3BucketName",
        "ParameterValue": "zipfileuploaddeploy",
        "UsePreviousValue": False,
        "ResolvedValue": "zipfileuploaddeploy"
    },
    {
        "ParameterKey": "QSS3KeyPrefix",
        "ParameterValue": "prefix/",
        "UsePreviousValue": False,
        "ResolvedValue": "prefix/"
    },
    {
        "ParameterKey": "ZipFileName",
        "ParameterValue": lamdasZipFileName,
        "UsePreviousValue": False,
        "ResolvedValue": lamdasZipFileName
    }
]


updateTemplate("bubble", "template.yml", param)




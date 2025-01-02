# dicom/orthanc_api.py
import sys
import os.path as op
sys.path.insert(0, op.dirname(op.dirname(__file__)))

import requests
from requests.auth import HTTPBasicAuth
import config



class OrthancAPI:
    def __init__(self):
        self.base_url = config.ORTHANC_HTTP_CONFIG['url']
        self.auth = HTTPBasicAuth(config.ORTHANC_HTTP_CONFIG['username'],
                                  config.ORTHANC_HTTP_CONFIG['password'])

    def get_studies(self):
        response = requests.get(f"{self.base_url}/studies", auth=self.auth)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get studies: {response.status_code}")

    def get_study_details(self, study_id):
        response = requests.get(f"{self.base_url}/studies/{study_id}", auth=self.auth)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get study details: {response.status_code}")

    def delete_study(self, study_id):
        response = requests.delete(f"{self.base_url}/studies/{study_id}", auth=self.auth)
        if response.status_code == 200:
            return True
        else:
            raise Exception(f"Failed to delete study: {response.status_code}")

    def get_instance_tags(self, instance_id):
        response = requests.get(f"{self.base_url}/instances/{instance_id}/tags", auth=self.auth)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get instance tags: {response.status_code}")
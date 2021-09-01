import errno
import os
import yaml
import argparse
import re
import sys
import filecmp

header = """
file_version: '0.1'
"""

# Template for new service

def write_config(filename, **kwargs):
    template ="""
    {component_name}:
      application:
        deployment:
          name: warehouse-app
          namespace: warehouse-ns
          replicaCount: 1
          port: 8000
          commitId: {commit_id}
          image:
            repository: lolverae/warehouse_service
            tag: {docker_tag}
        service:
          namespace: warehouse-ns
          name: warehouse-app
          type: NodePort
          port: 8000
"""
    # Adding new service for given component in given manifest file
    with open(filename, 'r+') as yml_file:
        yaml_dict = yaml.safe_load(yml_file)
        comp_yaml_dict = yaml.safe_load(template.format(**kwargs))
        yaml_dict[kwargs.get('component_name')] = comp_yaml_dict[kwargs.get('component_name')]
        yml_file.seek(0)
        yml_file.write(yaml.dump(yaml_dict))
        yml_file.truncate()


def update_valuefiles(filename, **kwargs):

    assert kwargs
    component_name = kwargs.get('name')
    release = kwargs.get('release',"valuefiles")
    pre_manifest_file = release + '/' + 'manifest.yaml'

    # check if release folder exists. if no, create a folder       
    if not os.path.exists(release):
        sys.exit("Release "+release+" not found")

    # # reading pre-manifest file for later to be updated
    with open(pre_manifest_file, 'r') as fpm:
        y_ml = yaml.safe_load(fpm) or {}
    
    #  Version Update, after adding components data
    version = y_ml["file_version"]
    version = float(version) + float(0.1)
    version = "%.1f" % version
    y_ml["file_version"] = version
    with open(pre_manifest_file, 'w+') as f:
        yaml.dump(y_ml, f, default_flow_style=False)
    print("Updated Manifest File for Component %s with %s" % (component_name, kwargs.values()))

def update_manifest(component_name, docker_tag):
    #split docker tag to get release, version and commit_id
    separator  = len( re.findall('[-]', docker_tag) )
    #if release is not retreived default to master
    release = 'valuefiles'
    version=docker_tag
    commit_id=docker_tag

    # Define pre-manifest file path and access rights
    access_rights = 0o755
    pre_manifest_file = release + '/' + 'manifest.yaml'

    write_config(pre_manifest_file, component_name=component_name, docker_tag=docker_tag, commit_id=commit_id)
    write_config('manifest-template.yaml', component_name=component_name, docker_tag=docker_tag, commit_id=commit_id)
    # update pre manifest file    
    update_valuefiles('manifest.yaml', commitId=commit_id, version=version, tag=docker_tag, name=component_name)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("component_name", help="Pass Component Name that needs to be updated in manifest file")
    parser.add_argument("docker_tag", help="Pass Docker tag that needs to be updated in manifest file")
    arguments = parser.parse_args() 
    update_manifest(arguments.component_name, arguments.docker_tag)

if __name__ == "__main__":
    main()
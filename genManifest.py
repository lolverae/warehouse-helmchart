import errno
import os
import yaml
import argparse
import re

header = """
file_version: '0.1'
"""

# Template for new service

def write_config(filename, new_vertical, **kwargs):
    if new_vertical:
        template ="""{vertical_name}:
  {comp_name}:
    application:
        deployment:
            name: {comp_name}
            namespace: warehouse-ns
            replicaCount: 1
            port: {app_port}
            commitId: {commit_id}
            version: {version}
            image:
                repository: lolverae/warehouse_service
                tag: {docker_tag}
        service:
            namespace: warehouse-ns
            name: warehouse-app
            type: NodePort
            port: 8000
            nodePort: 30001
    database:
        deployment:
            name: {comp_name}
            namespace: warehouse-ns
            replicaCount: 1
            port: {db_port}
            image:
                repository: lolverae/warehouse_service
                tag: {docker_tag}

        service:
            namespace: warehouse-ns
            name: warehouse-app
            type: NodePort
            port: {db_port}
            nodePort: {db_nodeport}
"""
    # Adding new service for given component in given manifest file
    with open(filename, 'r+') as yml_file:
        yaml_dict = yaml.safe_load(yml_file)
        comp_yaml_dict = yaml.safe_load(template.format(**kwargs))
        yaml_dict[kwargs.get('vertical_name')][kwargs.get('comp_name')] = comp_yaml_dict[kwargs.get('comp_name')]
        yml_file.seek(0)
        yml_file.write(yaml.dump(yaml_dict))
        yml_file.truncate()

def new_service_check(comp_name, vertical, filename='deployment-manifest-template.yml'):
    with open(filename, 'r') as f:
        yaml_dict = yaml.safe_load(f) or {}
        if 'file_version' not in yaml_dict:
            with open(filename, 'w') as ymlfile:
                ymlfile.write(header.format())
    if vertical in yaml_dict:
        if comp_name in yaml_dict[vertical]:
            return 0
        else:
            return 1  # "Service: Not Found"
    else:
        return 2  # "Vertical: Not Found"

def update_pre_manifest(filename, vertical_name, **kwargs):
    assert kwargs
    comp_name = kwargs.get('name')
    release = kwargs.get('release')
    pre_manifest_file = release + '/' + 'pre-manifest.yml'

    # check if release folder exists. if no, create a folder       
    if not os.path.exists(release):
        sys.exit("Release "+release+" not found")

    # reading pre-manifest file for later to be updated
    with open(pre_manifest_file, 'r') as fpm:  
        y_ml = yaml.safe_load(fpm) or {}
    
    # reading deployment-manifest-template to retain all other K-V, apart from dockerTag
    with open(filename, 'r') as f:  
        yaml_dict = yaml.safe_load(f) or {}

    # Updating deployment-manifest-template file with given component's values.
    yaml_dict[vertical_name][comp_name].update(kwargs)

    # Using intermediate dictionary to load updated component's details. This will have all other K-V from deployment
    # template but docker-tag, version and commit number from given (build).
    t_yml = yaml_dict[vertical_name][comp_name]
    
    # Updating intermediate dict. to pre-manifest dict to write final Yaml with updated value.
    y_ml[vertical_name][comp_name].update(t_yml)
    
    #  Version Update, after adding components data
    version = y_ml["file_version"]
    version = float(version) + float(0.1)
    version = "%.1f" % version
    y_ml["file_version"] = version
    with open(pre_manifest_file, 'w') as f:
        yaml.dump(y_ml, f, default_flow_style=False)
    print("Updated Manifest File for Component %s with %s" % (comp_name, kwargs.values()))

def update_create_manifest(comp_name, docker_tag, vertical_name):   
    #split docker tag to get release, version and commit_id
    separator  = len( re.findall('[-]', docker_tag) )    
    #if release is not retreived default to master
    release = 'master'
    if separator == 3:
        release = docker_tag.split('-')[1]
        version = docker_tag.split('-')[2]
        commit_id = docker_tag.split('-')[3]
        ver_len=len(re.findall('[.]', version))
        commit_length=len(commit_id)

        if not ( commit_length == 7):            
            print("Not Approved Commit_length: (!= 7) :: Setting it with Docker_Tag ::")
            commit_id=docker_tag
        if not ( ver_len == 2):
            print("Not Approved Version Length: (!=x.y.z) :: Setting it with Docker_Tag ::")
            version=docker_tag            
    else:
        print ("Given Docker-Tag not following expected format <<TAG-RELASE_BRANCH-VERSION-COMMIT_ID>>")
        version=docker_tag
        commit_id=docker_tag

    #if vertical_name is not retreived default to services
    if vertical_name is None:
        vertical_name = 'services'

    # Define pre-manifest file path and access rights
    access_rights = 0o755
    pre_manifest_file = release + '/' + 'pre-manifest.yml'

    # check if release folder exists. if no, create a folder       
    if not os.path.exists(release):
        try:
            os.makedirs(release, access_rights)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    #Check if pre manifest file exists. if no, create a file       
    if not os.path.exists(pre_manifest_file):
        try:
            with open(pre_manifest_file, 'a+') as f:
                f.write(header)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    #Check if the service is new to manifest file
    new_service = new_service_check(comp_name,vertical_name,pre_manifest_file)

    #if vertical & service not found
    if new_service == 1 or new_service == 2:
        if new_service == 2: 
            write_config(pre_manifest_file, True, comp_name=comp_name, docker_tag=docker_tag, commit_id=commit_id, version=version, vertical_name=vertical_name)
            write_config('deployment-manifest-template.yml', True, comp_name=comp_name, docker_tag=docker_tag, commit_id=commit_id, version=version, vertical_name=vertical_name)
        else:
            write_config(pre_manifest_file, False, comp_name=comp_name, docker_tag=docker_tag, commit_id=commit_id, version=version, vertical_name=vertical_name)
            write_config('deployment-manifest-template.yml', False, comp_name=comp_name, docker_tag=docker_tag, commit_id=commit_id, version=version, vertical_name=vertical_name)
    # update pre manifest file    
    update_pre_manifest('deployment-manifest-template.yml', vertical_name, dockerTag=docker_tag, version=version, commitId=commit_id, name=comp_name, release=release)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("comp_name", help="Pass Component Name that needs to be updated in manifest file")
    parser.add_argument("docker_tag", help="Pass Docker tag that needs to be updated in manifest file")
    parser.add_argument('vertical_name', nargs='?', const="services", help="Pass vertical that the components fall under. Defaults to services")
    arguments = parser.parse_args() 
    update_create_manifest(arguments.comp_name, arguments.docker_tag, arguments.vertical_name)    

if __name__ == "__main__":
    main()
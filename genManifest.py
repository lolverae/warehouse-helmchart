import errno
import os
import yaml
import argparse
import re
import sys

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
                name: warehouse-db
                namespace: warehouse-ns
                replicaCount: 1
                port: 5984
                image:
                    repository: lolverae/warehouse_service
                    tag: {docker_tag}
            service:
                namespace: warehouse-ns
                name: warehouse-app
                type: NodePort
                port: 5984
                nodePort: 30001
"""
    # Adding new service for given component in given manifest file
    with open(filename, 'r+') as yml_file:
        yaml_dict = yaml.safe_load(yml_file)
        comp_yaml_dict = yaml.safe_load(template.format(**kwargs))
        yaml_dict[kwargs.get('component_name')] = comp_yaml_dict[kwargs.get('component_name')]
        print(yaml_dict)
        yml_file.seek(0)
        yml_file.write(yaml.dump(yaml_dict))
        yml_file.truncate()

def new_service_check(component_name, filename='pre-manifest.yaml'):
    with open(filename, 'r') as f:
        yaml_dict = yaml.safe_load(f) or {}
        if 'file_version' not in yaml_dict:
            with open(filename, 'w') as ymlfile:
                ymlfile.write(header.format())
        if component_name in yaml_dict:
            return 0
        else:
            return 1  # "Service: Not Found"

def update_pre_manifest(filename, **kwargs):
    print(filename)
    print(kwargs)

    assert kwargs
    component_name = kwargs.get('name')
    release = kwargs.get('release',"master")
    print(release, component_name)
    pre_manifest_file = release + '/' + 'pre-manifest.yaml'

    # check if release folder exists. if no, create a folder       
    if not os.path.exists(release):
        sys.exit("Release "+release+" not found")

    # reading pre-manifest file for later to be updated
    with open(pre_manifest_file, 'r') as fpm:
        y_ml = yaml.safe_load(fpm) or {}
    
    # reading manifest-template to retain all other K-V, apart from dockerTag
    with open(filename, 'r') as f:  
        yaml_dict = yaml.safe_load(f) or {}
        
    # Updating manifest-template file with given component's values.
    yaml_dict[component_name].update(kwargs)

    # Using intermediate dictionary to load updated component's details. This will have all other K-V from deployment
    # template but docker-tag, version and commit number from given (build).
    t_yml = yaml_dict[component_name]
    
    # Updating intermediate dict. to pre-manifest dict to write final Yaml with updated value.
    y_ml[component_name].update(t_yml)
    
    #  Version Update, after adding components data
    version = y_ml["file_version"]
    version = float(version) + float(0.1)
    version = "%.1f" % version
    y_ml["file_version"] = version
    with open(pre_manifest_file, 'w') as f:
        yaml.dump(y_ml, f, default_flow_style=False)
    print("Updated Manifest File for Component %s with %s" % (component_name, kwargs.values()))

def update_create_manifest(component_name, docker_tag):
    print(component_name, docker_tag)   
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


    # Define pre-manifest file path and access rights
    access_rights = 0o755
    pre_manifest_file = release + '/' + 'pre-manifest.yaml'

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
    new_service = new_service_check(component_name,pre_manifest_file)

    write_config(pre_manifest_file, component_name=component_name, docker_tag=docker_tag, commit_id=commit_id, version=version)
    write_config('manifest-template.yaml', component_name=component_name, docker_tag=docker_tag, commit_id=commit_id, version=version)
    # update pre manifest file    
    update_pre_manifest('pre-manifest.yaml', dockerTag=docker_tag, name=component_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("component_name", help="Pass Component Name that needs to be updated in manifest file")
    parser.add_argument("docker_tag", help="Pass Docker tag that needs to be updated in manifest file")
    arguments = parser.parse_args() 
    update_create_manifest(arguments.component_name, arguments.docker_tag)



if __name__ == "__main__":
    main()
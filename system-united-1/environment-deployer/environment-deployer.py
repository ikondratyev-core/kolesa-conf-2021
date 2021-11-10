import json
import sys
import urllib2
import yaml
import copy
import os
import subprocess
import ssl

ns_name = sys.argv[1]
token = sys.argv[2]
root_url = sys.argv[3]
project = sys.argv[4]
storage_rootpath = os.getenv('DEPLOYER_STORAGE_ROOTPATH', "/srv")
v1_url = "{0}/api/v1/namespaces/".format(root_url)
v1beta_url = "{0}/apis/extensions/v1beta1/namespaces/".format(root_url)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

pgweb = {}
pgweblist = []


def request(url, data, method):
    print ("===============================================")
    print "EXECUTING: {0} {1}".format(method, url)
    print "  DATA: {0}".format(json.dumps(data))
    req = urllib2.Request(url)
    req.add_header('Authorization', 'Bearer ' + token)

    if method == "post":
        req.add_header('Content-Type', 'application/json')
        response = urllib2.urlopen(req, json.dumps(data), context=ctx)
    elif method == "patch":
        req.get_method = lambda: 'PATCH'
        req.add_header('Content-Type', 'application/strategic-merge-patch+json')
        response = urllib2.urlopen(req, json.dumps(data), context=ctx)
    elif method == "put":
        req.get_method = lambda: 'PUT'
        req.add_header('Content-Type', 'application/json')
        response = urllib2.urlopen(req, json.dumps(data), context=ctx)            
    elif method == "get":
        response = json.loads(urllib2.urlopen(req, context=ctx).read())
        return response
    elif method == "delete":
        req.get_method = lambda: 'DELETE'
        req.add_header('Content-Type', 'application/json')
        response = json.loads(urllib2.urlopen(req, context=ctx).read())
    
    if method == "put":
        print "    RESPONSE: {0} {1} {2} {3}".format(response.code, data["metadata"]["name"], data["kind"], response.msg)
    elif method == "delete":
        print "    RESPONSE: {0}".format("delete")
    else:
        print "    RESPONSE: {0} {1} {2} {3}".format(response.code, data["metadata"]["name"], data["kind"], response.msg)
    print ("===============================================")


def fulldeploy(filepath, image, version, svc, job, db, env, dump, method, dbmove, resources, replicas, ports, bgdeploy, mount, args, probes):
#probes_enabled=True):
    url = v1_url + ns_name + '/' + job
    with open(filepath) as f:
        y = yaml.load(f.read())
        y["metadata"]["namespace"] = ns_name      
        if job == "":
            url = v1_url          
            y["metadata"]["name"] = ns_name            
        elif job == "deployments":
            y["spec"]["template"]["spec"]["containers"][0]["env"] = [
                {
                  "name": "HOSTNAME",
                  "valueFrom": {
                    "fieldRef": {
                      "fieldPath": "metadata.name"
                    }
                  }
                },
                {
                  "name": "ENVIRONMENT_NAME",
                  "valueFrom": {
                    "fieldRef": {
                      "fieldPath": "metadata.namespace"
                    }
                  }
                }
              ]
            if version == "stable":
                y["spec"]["template"]["spec"]["containers"][0]["imagePullPolicy"] = "Always"
            if method == "post":
                url = v1beta_url + ns_name + '/' + job
            elif method == "put":              
                url = v1beta_url + ns_name + '/' + job + "/" + svc            

            y["metadata"]["name"] = svc
            y["spec"]["template"]["metadata"]["labels"]["app"] = svc
            y["spec"]["template"]["spec"]["containers"][0]["name"] = svc
            y["spec"]["template"]["spec"]["containers"][0]["image"] = image + ":" + version

            if db:
                rsvc = svc.replace('-', '_')
                rsvc = rsvc.replace('cbs_', '')
                if svc == "cbs-executor":
                    rsvc = 'executor'
                    y["spec"]["template"]["spec"]["containers"][0]["env"].extend([
                        {"name": "DB_HOST", "value": "pgdb-" + rsvc.replace('_', '-')},
                        {"name": "DB_NAME", "value": rsvc},
                        {"name": "DBMIGRATION_USER", "value": "db_core"},
                        {"name": "DBMIGRATION_PASS", "value": "df464DFL360aleKKfw3516KJ3KL"},
                        {"name": "DB_USER", "value": "cbs_user"},
                        {"name": "DB_PASS", "value": "k392ZHeNMGxWo7HTWc8GznYiHbB"},
                    ])
                else:
                    y["spec"]["template"]["spec"]["containers"][0]["env"].extend([
                        {"name": "DB_HOST", "value": "pgdb-" + rsvc.replace('_', '-')},
                        {"name": "DB_NAME", "value": rsvc},
                        {"name": "DBMIGRATION_USER", "value": rsvc},
                        {"name": "DBMIGRATION_PASS", "value": "df464DFL360aleKKfw3516KJ3KL"},
                        {"name": "DB_USER", "value": rsvc + "_user"},
                        {"name": "DB_PASS", "value": "k392ZHeNMGxWo7HTWc8GznYiHbB"},
                    ]) 
                    pgweb[rsvc + ".toml"] = "host = \"" + "pgdb-" + rsvc.replace('_', '-') + "\"\nport = 5432\nuser = \"developer\"\npassword = \"2ss0zuFwem\"\ndatabase = \"" + rsvc + "\"\nssl = \"disable\"\n"
                if env:     
                    for item in env:
                        y["spec"]["template"]["spec"]["containers"][0]["env"].append(item)
                if dbmove:
                    dbdeploy(svc, copy.deepcopy(y["spec"]["template"]["spec"]["containers"][0]["env"]), dump, job, "post") 
                elif not dbmove:
                    dbdeploy(svc, copy.deepcopy(y["spec"]["template"]["spec"]["containers"][0]["env"]), dump, job, "put") 
            elif not db and method == "put" and dbmove:
                rsvc = svc.replace('cbs-', '')
                remover("pgdb-" + rsvc, False, "delete")
            elif env:                
                y["spec"]["template"]["spec"]["containers"][0]["env"].extend(env)
            if resources:
                y["spec"]["template"]["spec"]["containers"][0]["resources"] = resources
            if replicas:
                y["spec"]["replicas"] = replicas
                if not bgdeploy:
                    y["spec"]["strategy"]["rollingUpdate"]["maxSurge"] = replicas
                    y["spec"]["strategy"]["rollingUpdate"]["maxUnavailable"] = 0
            if mount:
                if svc == "consul-cluster":
                    if "hostPath" in mount["volumes"][1]:
                        mount["volumes"][1]["hostPath"]["path"] = mount["volumes"][1]["hostPath"]["path"].replace("$CI_BUILD_REF_SLUG", ns_name).replace("$CI_PROJECT_NAMESPACE", project)
                y["spec"]["template"]["spec"]["containers"][0]["volumeMounts"] = mount["volumeMounts"]
                y["spec"]["template"]["spec"]["volumes"] = mount["volumes"]
                print(y)
            if probes != False:
	        if probes:
    	            y["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = probes["livenessProbe"]
        	    y["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = probes["readinessProbe"]
                else:
            	    y["spec"]["template"]["spec"]["containers"][0]["livenessProbe"] = {
            	        'initialDelaySeconds': 30,
            	        'failureThreshold': 10,
            	        'periodSeconds': 30,
            	        'tcpSocket': {
            	            'port': ports[0]["port"] if ports else 8080
            	        },
            	        '#timeoutSeconds': 3
            	    }
        	    y["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = {
        	        'initialDelaySeconds': 30,
        	        'failureThreshold': 10,
        	        'periodSeconds': 30,
        	        'tcpSocket': {
        	            'port': ports[0]["port"] if ports else 8080
        	        },
        	        'timeoutSeconds': 3
        	    }
            if args:
                y["spec"]["template"]["spec"]["containers"][0]["args"] = args                                              
            if svc == "pgweb":
                fulldeploy("yaml/configmap-pgweb.yaml", "", "", "", "configmaps", "", "", "", "post", "", "", "", "", "", "", "")
                for i in pgweb:
                    pgweblist.append({"key": i, "path": i})
                    y["spec"]["template"]["spec"]["volumes"][0]["configMap"]["items"] = pgweblist
        elif job == "services":         
            y["metadata"]["name"] = svc
            y["metadata"]["labels"]["app"] = svc
            y["spec"]["selector"]["app"] = svc
            if ports:
                y["spec"]["ports"] = ports
            if method == "put":             
                url = v1_url + ns_name + '/' + job + "/" + svc 
                opt = (svcopt(svc))
                y["metadata"]["resourceVersion"] = opt[0]
                y["spec"]["clusterIP"] = opt[1]
        
        elif job == "configmaps" and y["metadata"]["name"] == "pgweb-init":
            y["data"] = pgweb

        request(url, y, method)


def svcopt(svc):
    url = v1_url + ns_name + '/services/' + svc
    response = request(url, "", "get")
    return response["metadata"]["resourceVersion"], response["spec"]["clusterIP"]


def dbdeploy(svc, dbconect, dump, job, method):
    
    if job == "deployments":
        file_name = "db_deploy.yaml"
        url = v1beta_url
    elif job == "services":
        file_name = "db_svc.yaml"
        url = v1_url

    if method == "post":
        url = url + ns_name + '/' + job
    elif method == "put":
        url = url + ns_name + '/' + job + "/" + "pgdb-" + svc.replace('cbs-', '')

    with open("yaml/" + file_name) as f:
        
        if job == "deployments":
            y = yaml.load(f.read())
            y["metadata"]["namespace"] = ns_name
            y["metadata"]["name"] = "pgdb-" + svc.replace('cbs-', '')
            y["spec"]["template"]["metadata"]["labels"]["app"] = "pgdb-" + svc.replace('cbs-', '')
            y["spec"]["template"]["spec"]["containers"][0]["name"] = "pgdb-" + svc.replace('cbs-', '')
            y["spec"]["template"]["spec"]["volumes"][1]["hostPath"]["path"] = storage_rootpath + "/" + project + "/" + ns_name + "/postgres/" + svc.replace('cbs-', '') + "-data"
            y["spec"]["template"]["spec"]["containers"][0]["env"] = dbconect
            y["spec"]["template"]["spec"]["containers"][0]["env"].append({"name": "PGDATA", "value": "/var/lib/postgresql/data/" + svc.replace('cbs-', '')})
            y["spec"]["template"]["spec"]["containers"][0]["env"].append({"name": "POSTGRES_PASSWORD", "value": "fs925msJKF92mKQ21dgf0skJQ1c"})
            y["spec"]["template"]["spec"]["containers"][0]["env"].append({"name": "DBDEV_USER", "value": "developer"})
            y["spec"]["template"]["spec"]["containers"][0]["env"].append({"name": "DBDEV_PASS", "value": "2ss0zuFwem"})
            if dump: 
                dumpname = svc.replace('cbs-', '')
                dumpname = dumpname.replace('-', '_')
                y["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append({'mountPath': '/db-dumps/' + dumpname + '.dump', 'name': 'dumps', 'readOnly': True})
                y["spec"]["template"]["spec"]["volumes"].append({'hostPath': {'path': storage_rootpath + '/dumps/' + dumpname + '.dump'}, 'name': 'dumps'})
                y["spec"]["template"]["spec"]["volumes"][0]["configMap"]["items"].append({'path': 'loaddump.sh', 'key': 'loaddump.sh'})
            
            y["spec"]["template"]["spec"]["volumes"][0]["configMap"]["items"].append({'path': 'z_devUser.sh', 'key': 'z_devUser.sh'})

            dbdeploy(svc, dbconect, dump, "services", method)
        elif job == "services":
            y = yaml.load(f.read())
            y["metadata"]["namespace"] = ns_name
            y["metadata"]["name"] = "pgdb-" + svc.replace('cbs-', '')
            y["metadata"]["labels"]["app"] = "pgdb-" + svc.replace('cbs-', '')
            y["spec"]["selector"]["app"] = "pgdb-" + svc.replace('cbs-', '')
            y["spec"]["ports"][0]["name"] = "pgdb-" + svc.replace('cbs-', '') + '-ext'

            if method == "put":
                opt = (svcopt("pgdb-" + svc.replace('cbs-', '')))
                y["metadata"]["resourceVersion"] = opt[0]
                y["spec"]["clusterIP"] = opt[1]

        request(url, y, method)


def deployer(service_name, manifest_file, method, dbmove):

    svctype = "service"     

    if "services" in manifest_file:
        data = manifest_file["services"][service_name]
    else:        
        data = manifest_file

    # default values
    env = ports = resources = replicas = bgdeploy = mount = args = probes = ""

    if "ports" in data:                        
        ports = data["ports"]            

    if "env" in data:                     
        env = data["env"]

    if "replicas" in data:             
        replicas = data["replicas"]        

    if "resources" in data:
        resources = data["resources"]

    if "bgdeploy" in data:                        
        bgdeploy = data["bgdeploy"]     
    
    if "mount" in data:                        
        mount = data["mount"]       
    
    if "args" in data:                        
        args = data["args"]

    if "probes" in data:                        
        probes = data["probes"]

    #if 'probes_enabled' in data:
        #probes_enabled = data['probesEnabled'].strip().lower() == 'true'
    
    fulldeploy(
        "yaml/" + svctype + "_deploy.yaml", data["image"], data["version"],
        service_name, "deployments", data["requiresDb"], env, data["dumpDb"], method,
        dbmove, resources, replicas, ports, bgdeploy, mount, args, probes)
        #probes_enabled=probes_enabled)

    fulldeploy(
        "yaml/" + svctype + "_svc.yaml", "", "", service_name, "services", data["requiresDb"],
        "", "", method, dbmove, "", "", ports, "", "", "", "")


def remover(svc_name, remdb, method):    

    if remdb:
        remover('pgdb-' + svc_name.replace('cbs-', ''), False, "delete")        

    url = v1beta_url + ns_name + '/' + "deployments" + "/" + svc_name
    request(url, "", method)

    url = v1beta_url + ns_name + '/' + "replicasets" + "/" + "?labelSelector=app%3D" + svc_name
    response = request(url, "", "get")
    for items in response["items"]:        
        url = v1beta_url + ns_name + '/' + "replicasets" + "/" + items["metadata"]["name"]
        request(url, "", method)

    url = v1_url + ns_name + '/' + "pods" + "/" + "?labelSelector=app%3D" + svc_name
    response = request(url, "", "get")
    for items in response["items"]:        
        url = v1_url + ns_name + '/' + "pods" + "/" + items["metadata"]["name"]
        request(url, "", method)
    
    url = v1_url + ns_name + '/' + "services" + "/" + svc_name
    request(url, "", method)   
              
    
try:
    fulldeploy("yaml/namespace.yaml", "", "", "", "", "", "", "", "post", "", "", "", "", "", "", "", "")

except urllib2.HTTPError:

    with open("manifest.yml") as f_current:
        manifest_cur = yaml.load(f_current.read())

    subprocess.call(["git", "checkout", "HEAD~1", "--", "manifest.yml"])
    
    with open("manifest.yml") as f_previous:
        manifest_pre = yaml.load(f_previous.read())

    mvsvc = set(manifest_cur["services"]) ^ set(manifest_pre["services"])
    
    for service in manifest_cur["services"]:
        for service_add in mvsvc:
            if service == service_add:                
                deployer(service, manifest_cur["services"][service], "post", True)
    
    for service in manifest_pre["services"]:
        for service_del in mvsvc:
            if service == service_del:
                remover(service, manifest_pre["services"][service]["requiresDb"], "delete")

    for service_cur in manifest_cur["services"]:
        for service_pre in manifest_pre["services"]:
            if service_cur == service_pre:
                if manifest_cur["services"][service_cur] != manifest_pre["services"][service_pre]:
                    if manifest_cur["services"][service_cur]["requiresDb"] != manifest_pre["services"][service_pre]["requiresDb"]:
                        deployer(service_cur, manifest_cur["services"][service_cur], "put", True)
                    else:
                        deployer(service_cur, manifest_cur["services"][service_cur], "put", False)
else:
    fulldeploy("yaml/secret.yaml", "", "", "", "secrets", "", "", "", "post", "", "", "", "", "", "", "", "")
    fulldeploy("yaml/configmap.yaml", "", "", "", "configmaps", "", "", "", "post", "", "", "", "", "", "", "", "")
    with open("manifest.yml") as f:
        y = yaml.load(f.read())
        for service in y["services"]:
            deployer(service, y, "post", True)

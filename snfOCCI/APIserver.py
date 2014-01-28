# Copyright 2012-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#     copyright notice, this list of conditions and the following
#     disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials
#     provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.


#!/usr/bin/env python

import sys
from optparse import OptionParser, OptionValueError
import string
import sqlite3
import eventlet
from eventlet import wsgi
import os
import json
import uuid

from snfOCCI.registry import snfRegistry
from snfOCCI.compute import ComputeBackend
from snfOCCI.config import SERVER_CONFIG, KAMAKI_CONFIG, VOMS_CONFIG
import snf_voms
from snfOCCI.network import NetworkBackend, IpNetworkBackend, IpNetworkInterfaceBackend, NetworkInterfaceBackend


from kamaki.clients.compute import ComputeClient
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients import astakos
from kamaki.clients import ClientError
from kamaki.cli import config as kamaki_config

from occi.core_model import Mixin, Resource
from occi.backend import MixinBackend
from occi.extensions.infrastructure import COMPUTE, START, STOP, SUSPEND, RESTART, RESOURCE_TEMPLATE, OS_TEMPLATE, NETWORK, IPNETWORK, NETWORKINTERFACE,IPNETWORKINTERFACE 
from occi import wsgi
from occi.exceptions import HTTPError
from occi import core_model

from wsgiref.simple_server import make_server
from wsgiref.validate import validator
from webob import Request
from pprint import pprint


class MyAPP(wsgi.Application):
    '''
    An OCCI WSGI application.
    '''

    def __init__(self):
        """
        Initialization of the WSGI OCCI application for synnefo
        """
        global ENABLE_VOMS, VOMS_DB
        ENABLE_VOMS = VOMS_CONFIG['enable_voms']
        super(MyAPP,self).__init__(registry=snfRegistry())
        self._register_backends()
        VALIDATOR_APP = validator(self)
         
        
    def _register_backends(self):
        COMPUTE_BACKEND = ComputeBackend()
        NETWORK_BACKEND = NetworkBackend() 
        NETWORKINTERFACE_BACKEND = NetworkInterfaceBackend()
        IPNETWORK_BACKEND = IpNetworkBackend()
        IPNETWORKINTERFACE_BACKEND = IpNetworkInterfaceBackend()
    
        self.register_backend(COMPUTE, COMPUTE_BACKEND)
        self.register_backend(START, COMPUTE_BACKEND)
        self.register_backend(STOP, COMPUTE_BACKEND)
        self.register_backend(RESTART, COMPUTE_BACKEND)
        self.register_backend(SUSPEND, COMPUTE_BACKEND)
        self.register_backend(RESOURCE_TEMPLATE, MixinBackend())
        self.register_backend(OS_TEMPLATE, MixinBackend())
       
        # Network related backends
        self.register_backend(NETWORK, NETWORK_BACKEND)
        self.register_backend(IPNETWORK, IPNETWORK_BACKEND)
        self.register_backend(NETWORKINTERFACE,NETWORKINTERFACE_BACKEND)
        self.register_backend(IPNETWORKINTERFACE, IPNETWORKINTERFACE_BACKEND)
     
        
    def refresh_images(self, snf, client):
        try:
            images = snf.list_images()
            for image in images:
                    IMAGE_ATTRIBUTES = {'occi.core.id': str(image['id'])}
                    IMAGE = Mixin("http://schemas.ogf.org/occi/os_tpl#", occify_terms(str(image['name'])), [OS_TEMPLATE],title='IMAGE' ,attributes = IMAGE_ATTRIBUTES)
                    self.register_backend(IMAGE, MixinBackend())
        except:
            raise HTTPError(404, "Unauthorized access")
      
    def refresh_flavors(self, snf, client):
        
        flavors = snf.list_flavors()
        for flavor in flavors:
            details = snf.get_flavor_details(flavor['id'])
            FLAVOR_ATTRIBUTES = {'occi.core.id': flavor['id'],
                                 'occi.compute.cores': str(details['vcpus']),
                                 'occi.compute.memory': str(details['ram']),
                                 'occi.storage.size': str(details['disk']),
                                 }
            FLAVOR = Mixin("http://schemas.ogf.org/occi/resource_tpl#", str(flavor['name']), [RESOURCE_TEMPLATE], attributes = FLAVOR_ATTRIBUTES)
            self.register_backend(FLAVOR, MixinBackend())
            
            
    def refresh_flavors_norecursive(self, snf, client):
        flavors = snf.list_flavors(True)
        print "Retrieving details for each image id"
        for flavor in flavors:
            FLAVOR_ATTRIBUTES = {'occi.core.id': flavor['id'],
                                 'occi.compute.cores': str(flavor['vcpus']),
                                 'occi.compute.memory': str(flavor['ram']),
                                 'occi.storage.size': str(flavor['disk']),
                                 }
             
            FLAVOR = Mixin("http://schemas.ogf.org/occi/resource_tpl#", occify_terms(str(flavor['name'])), [RESOURCE_TEMPLATE], title='FLAVOR',attributes = FLAVOR_ATTRIBUTES)
            self.register_backend(FLAVOR, MixinBackend())
            
    def refresh_network_instances(self,client):
        network_details = client.list_networks(detail='True')
        resources = self.registry.resources
        occi_keys = resources.keys()
         
        for network in network_details:
            if '/network/'+str(network['id']) not in occi_keys:
                netID = '/network/'+str(network['id'])   
                snf_net = core_model.Resource(netID,
                                           NETWORK,
                                           [IPNETWORK])
                
                snf_net.attributes['occi.core.id'] = str(network['id']) 
               
                #This info comes from the network details
                snf_net.attributes['occi.network.state'] = str(network['status'])
                snf_net.attributes['occi.network.gateway'] = ''
               
                if network['public'] == True:
                    snf_net.attributes['occi.network.type'] = "Public = True"
                else:
                    snf_net.attributes['occi.network.type'] = "Public = False"
                    
                self.registry.add_resource(netID, snf_net, None)       
            
        
    
    def refresh_compute_instances(self, snf, client):
        '''Syncing registry with cyclades resources'''
        
        servers = snf.list_servers()
        snf_keys = []
        for server in servers:
            snf_keys.append(str(server['id']))

        resources = self.registry.resources
        occi_keys = resources.keys()
        
        print occi_keys
        for serverID in occi_keys:
            if '/compute/' in serverID and resources[serverID].attributes['occi.compute.hostname'] == "":
                self.registry.delete_resource(serverID, None)
        
        occi_keys = resources.keys()
        
            
        #Compute instances in synnefo not available in registry
        diff = [x for x in snf_keys if '/compute/'+x not in occi_keys]
        
        for key in diff:

            details = snf.get_server_details(int(key))
            flavor = snf.get_flavor_details(details['flavor']['id'])
            
            try:
                print "line 65:Finished getting image details for VM "+key+" with ID" + str(details['flavor']['id'])
                image = snf.get_image_details(details['image']['id'])
                
                for i in self.registry.backends:
                    if i.term ==  occify_terms(str(image['name'])):
                        rel_image = i
                    if i.term ==  occify_terms(str(flavor['name'])):
                        rel_flavor = i

                        
                resource = Resource(key, COMPUTE, [rel_flavor, rel_image])
                resource.actions = [START]
                resource.attributes['occi.core.id'] = key
                resource.attributes['occi.compute.state'] = 'inactive'
                resource.attributes['occi.compute.architecture'] = SERVER_CONFIG['compute_arch']
                resource.attributes['occi.compute.cores'] = str(flavor['vcpus'])
                resource.attributes['occi.compute.memory'] = str(flavor['ram'])
                resource.attributes['occi.core.title'] = str(details['name'])
                networkIDs = details['addresses'].keys()
                if len(networkIDs)>0: 
                    resource.attributes['occi.compute.hostname'] =  str(details['addresses'][networkIDs[0]][0]['addr'])
                else:
                    resource.attributes['occi.compute.hostname'] = ""
                    
                self.registry.add_resource(key, resource, None)  
                
                for netKey in networkIDs:
                    link_id = str(uuid.uuid4())
                    NET_LINK = core_model.Link("http://schemas.ogf.org/occi/infrastructure#networkinterface" + link_id,
                                               NETWORKINTERFACE,
                                               [IPNETWORKINTERFACE], resource,
                                               self.registry.resources['/network/'+str(netKey)])
                    
                    for version in details['addresses'][netKey]:
                       
                        ip4address = ''
                        ip6address = ''

                        if version['version']==4:
                            ip4address = str(version['addr'])
                            allocheme = str(version['OS-EXT-IPS:type'])
                        elif version['version']==6:
                            ip6address = str(version['addr'])
                            allocheme = str(version['OS-EXT-IPS:type'])
                   
                    if 'attachments' in details.keys():
                        for item in details['attachments']:
                            NET_LINK.attributes ={'occi.core.id':link_id,
                                          'occi.networkinterface.allocation' : allocheme,
                                          'occi.networking.interface': str(item['id']),
                                          'occi.networkinterface.mac' : str(item['mac_address']),
                                          'occi.networkinterface.address' : ip4address,
                                          'occi.networkinterface.ip6' :  ip6address                      
                                      }
                    elif  len(details['addresses'][netKey])>0:
                        NET_LINK.attributes ={'occi.core.id':link_id,
                                          'occi.networkinterface.allocation' : allocheme,
                                          'occi.networking.interface': '',
                                          'occi.networkinterface.mac' : '',
                                          'occi.networkinterface.address' : ip4address,
                                          'occi.networkinterface.ip6' :  ip6address                      
                                      }
    
                    else:
                        NET_LINK.attributes ={'occi.core.id':link_id,
                                          'occi.networkinterface.allocation' : '',
                                          'occi.networking.interface': '',
                                          'occi.networkinterface.mac' : '',
                                          'occi.networkinterface.address' :'',
                                          'occi.networkinterface.ip6' : '' }
                                      
                    resource.links.append(NET_LINK)
                    self.registry.add_resource(link_id, NET_LINK, None)
                     
                
            except ClientError as ce:
                if ce.status == 404:
                    print('Image not found (probably older version')
                    continue
                else:
                    raise ce
                  
        #Compute instances in registry not available in synnefo
        diff = [x for x in occi_keys if x[9:] not in snf_keys]
        for key in diff:
            if '/network/' not in key:
                self.registry.delete_resource(key, None)


    def __call__(self, environ, response):
        
        # Enable VOMS Authorization
        print "snf-occi application has been called!"
        
        req = Request(environ) 
        auth_endpoint = 'snf-auth uri=\'https://'+SERVER_CONFIG['hostname']+':5000/main\''
        
        if not req.environ.has_key('HTTP_X_AUTH_TOKEN'):
              
                print "Error: An authentication token has not been provided!"
                status = '401 Not Authorized'
                headers = [('Content-Type', 'text/html'),('Www-Authenticate',auth_endpoint)]        
                response(status,headers)               
                return [str(response)]
   
   
        if ENABLE_VOMS:
                
            if req.environ.has_key('HTTP_X_AUTH_TOKEN'):
               
                environ['HTTP_AUTH_TOKEN']= req.environ['HTTP_X_AUTH_TOKEN']
                compClient = ComputeClient(KAMAKI_CONFIG['compute_url'], environ['HTTP_AUTH_TOKEN'])
                cyclClient = CycladesClient(KAMAKI_CONFIG['compute_url'], environ['HTTP_AUTH_TOKEN'])
                netClient = CycladesNetworkClient(KAMAKI_CONFIG['network_url'], environ['HTTP_AUTH_TOKEN'])

                try:
                    #Up-to-date flavors and images
                    self.refresh_images(compClient,cyclClient)           
                    self.refresh_flavors_norecursive(compClient,cyclClient)
                    self.refresh_network_instances(netClient)
                    self.refresh_compute_instances(compClient,cyclClient)
                    # token will be represented in self.extras
                    return self._call_occi(environ, response, security = None, token = environ['HTTP_AUTH_TOKEN'], snf = compClient, client = cyclClient)
                except HTTPError:
                    print "Exception from unauthorized access!"
                    status = '401 Not Authorized'
                    headers = [('Content-Type', 'text/html'),('Www-Authenticate',auth_endpoint)]
                    response(status,headers)
                    return [str(response)]

            else:
                
                #raise HTTPError(404, "Unauthorized access")
                status = '401 Not Authorized'
                headers = [('Content-Type', 'text/html'),('Www-Authenticate',auth_endpoint)]
                response(status,headers)
                return [str(response)]

        else:  
            compClient = ComputeClient(KAMAKI_CONFIG['compute_url'], environ['HTTP_AUTH_TOKEN'])
            cyclClient = CycladesClient(KAMAKI_CONFIG['compute_url'], environ['HTTP_AUTH_TOKEN'])

            #Up-to-date flavors and images
           
            self.refresh_images(compClient,cyclClient)
            
            self.refresh_flavors_norecursive(compClient,cyclClient)
            self.refresh_network_instances(cyclClient)
            self.refresh_compute_instances(compClient,cyclClient)
            
            # token will be represented in self.extras
            return self._call_occi(environ, response, security = None, token = environ['HTTP_AUTH_TOKEN'], snf = compClient, client = cyclClient)

def application(env, start_response):
    
    print "snf-occi will execute voms authentication"
    t =snf_voms.VomsAuthN()       
    (user_dn, user_vo, user_fqans) = t.process_request(env)
    print (user_dn, user_vo, user_fqans)
      
    env['HTTP_AUTH_TOKEN'] = get_user_token(user_dn)
   
    # Get user authentication details
    pool = False
    astakosClient = astakos.AstakosClient(env['HTTP_AUTH_TOKEN'], KAMAKI_CONFIG['astakos_url'] , use_pool = pool)

    user_details = astakosClient.authenticate()
    
    response = {'access': {'token':{'issued_at':'','expires': user_details['access']['token']['expires'] , 'id':env['HTTP_AUTH_TOKEN']},
                           'serviceCatalog': [],
                           'user':{'username': user_dn,'roles_links':user_details['access']['user']['roles_links'],'id': user_details['access']['user']['id'], 'roles':[], 'name':user_dn },
                           'metadata': {'is_admin': 0, 'roles': user_details['access']['user']['roles']}}}        
           
   
    status = '200 OK'
    headers = [('Content-Type', 'application/json')]        
    start_response(status,headers)

    body = json.dumps(response)
    print body
    return [body]


def app_factory(global_config, **local_config):
    """This function wraps our simple WSGI app so it
    can be used with paste.deploy"""
    return application

def tenant_application(env, start_response):
    
    print "snf-occi will return tenant information"
    if env.has_key('SSL_CLIENT_S_DN_ENV'):
        print env['SSL_CLIENT_S_DN_ENV'], env['SSL_CLIENT_CERT_ENV']    
 
    req = Request(env) 
    if req.environ.has_key('HTTP_X_AUTH_TOKEN'):
            env['HTTP_AUTH_TOKEN']= req.environ['HTTP_X_AUTH_TOKEN']
    else:
            raise HTTPError(404, "Unauthorized access") 
    # Get user authentication details
    print "@ refresh_user authentication details"
    astakosClient = astakos.AstakosClient(KAMAKI_CONFIG['astakos_url'], env['HTTP_AUTH_TOKEN'])
    user_details = astakosClient.authenticate()
   
    response = {'tenants_links': [], 'tenants':[{'description':'Instances of EGI Federated Clouds TF','enabled': True, 'id':user_details['access']['user']['id'],'name':'EGI_FCTF'}]}           
 
    status = '200 OK'
    headers = [('Content-Type', 'application/json')]        
    start_response(status,headers)

    body = json.dumps(response)
    print body
    return [body]


def tenant_app_factory(global_config, **local_config):
    """This function wraps our simple WSGI app so it
    can be used with paste.deploy"""
    return tenant_application


    
def occify_terms(term_name):
    '''
    Occifies a term_name so that it is compliant with GFD 185.
    '''
    term = term_name.strip().replace(' ', '_').replace('.', '-').lower()
    term=term.replace('(','_').replace(')','_').replace('@','_').replace('+','-_')
    return term

def get_user_token(user_dn):
        config = kamaki_config.Config()
        return config.get_cloud("default", "token")

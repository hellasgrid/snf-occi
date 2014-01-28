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


from snfOCCI.config import SERVER_CONFIG

from occi.backend import ActionBackend, KindBackend
from occi.extensions.infrastructure import START, STOP, SUSPEND, RESTART
from occi.exceptions import HTTPError


#Compute Backend for snf-occi-server

class MyBackend(KindBackend, ActionBackend):

    # Updating and Replacing compute instances not supported by Cyclades

    def update(self, old, new, extras):
        raise HTTPError(501, "Update is currently no applicable")

    def replace(self, old, new, extras):
        raise HTTPError(501, "Replace is currently no applicable")


class ComputeBackend(MyBackend):
    '''
    Backend for Cyclades/Openstack compute instances
    '''

    def create(self, entity, extras):

        #Creating new compute instance
        
        try:

            snf = extras['snf']

            for mixin in entity.mixins:
                if mixin.related[0].term == 'os_tpl':
                    image_id = mixin.attributes['occi.core.id']
                if mixin.related[0].term == 'resource_tpl':
                    flavor = mixin
                    flavor_id = mixin.attributes['occi.core.id']

            vm_name = entity.attributes['occi.core.title']
            info = snf.create_server(vm_name, flavor_id, image_id)
           
            entity.actions = [START]
            entity.attributes['occi.compute.state'] = 'inactive'
            entity.attributes['occi.core.id'] = str(info['id'])
            entity.attributes['occi.compute.architecture'] = SERVER_CONFIG['compute_arch']
            entity.attributes['occi.compute.cores'] = flavor.attributes['occi.compute.cores']
            entity.attributes['occi.compute.memory'] = flavor.attributes['occi.compute.memory']
           
            # entity.attributes['occi.compute.hostname'] = SERVER_CONFIG['hostname'] % {'id':info['id']}
            info['adminPass']= ""
            print info
            networkIDs = info['addresses'].keys()
                #resource.attributes['occi.compute.hostname'] = SERVER_CONFIG['hostname'] % {'id':int(key)}
            if len(networkIDs)>0:    
                entity.attributes['occi.compute.hostname'] =  str(info['addresses'][networkIDs[0]][0]['addr'])
            else:
                entity.attributes['occi.compute.hostname'] = ""
               
        except (UnboundLocalError, KeyError) as e:
            raise HTTPError(406, 'Missing details about compute instance')
            

    def retrieve(self, entity, extras):
        
        #Triggering cyclades to retrieve up to date information

        snf = extras['snf']

        vm_id = int(entity.attributes['occi.core.id'])
        vm_info = snf.get_server_details(vm_id)
        vm_state = vm_info['status']
        
        status_dict = {'ACTIVE' : 'active',
                       'STOPPED' : 'inactive',
                       'ERROR' : 'inactive',
                       'BUILD' : 'inactive',
                       'DELETED' : 'inactive',
                       }
        
        entity.attributes['occi.compute.state'] = status_dict[vm_state]
                
        if vm_state == 'ERROR':
            raise HTTPError(500, 'ERROR building the compute instance')

        else:
            if entity.attributes['occi.compute.state'] == 'inactive':
                entity.actions = [START]
            if entity.attributes['occi.compute.state'] == 'active': 
                entity.actions = [STOP, SUSPEND, RESTART]


    def delete(self, entity, extras):

        #Deleting compute instance

        snf = extras['snf']
        vm_id = int(entity.attributes['occi.core.id'])
        snf.delete_server(vm_id)


    def action(self, entity, action, extras):

        #Triggering action to compute instances

        client = extras['client']
        snf = extras['snf']

        vm_id = int(entity.attributes['occi.core.id'])
        vm_info = snf.get_server_details(vm_id)
        vm_state = vm_info['status']


        if vm_state == 'ERROR':
            raise HTTPError(500, 'ERROR building the compute instance')

        else:
            if action not in entity.actions:
                raise AttributeError("This action is currently no applicable.")
            
            elif action == START:
                print "Starting VM"
                client.start_server(vm_id)
                
            elif action == STOP:
                print "Stopping VM"
                client.shutdown_server(vm_id)
    
            elif action == RESTART:
                print "Restarting VM"
                snf.reboot_server(vm_id)

            elif action == SUSPEND:
                raise HTTPError(501, "This actions is currently no applicable")

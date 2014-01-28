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

SERVER_CONFIG = {
    'port': 8888,
    'hostname': '$vm_hostname$',
    'compute_arch': 'x86'
    }

KAMAKI_CONFIG = {
    'compute_url': 'https://cyclades.okeanos.grnet.gr/compute/v2.0/',
    'astakos_url': 'https://accounts.okeanos.grnet.gr/identity/v2.0/',
    'network_url': 'https://cyclades.okeanos.grnet.gr/network/v2.0'
}
        
VOMS_CONFIG = {
    'enable_voms' : 'True',           
    'voms_policy' : '/etc/snf/voms.json',
    'vomsdir_path' : '/etc/grid-security/vomsdir/',
    'ca_path': '/etc/grid-security/certificates/',
    'cert_dir' : '/etc/ssl/certs/',
    'key_dir' : '/etc/ssl/private/'               
}
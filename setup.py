from setuptools import setup

setup(
    name='snf-occi',
    version='0.1',
    description='OCCI to Openstack/Cyclades API bridge',
    url='http://code.grnet.gr/projects/snf-occi',
    license='BSD',
    packages = ['snfOCCI','snfOCCI.snf_voms'],
    entry_points = ''' 
        [paste.app_factory]
        snf_occi_app = snfOCCI:main
        ''',   
    )
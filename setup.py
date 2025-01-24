from setuptools import find_packages, setup

# minimal setup for brainscore
setup(
    name='your_head',
    packages=find_packages(
        include=['dorsalnet', 'dorsalnet.*'],
    ),
    include_package_data=True,
    package_data={
        '':[
            'dorsalnet/results',
        ]
    },
)
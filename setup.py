from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'speech_recognition_sherpa_onnx'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'sound_file'), glob('sound_file/*.wav')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sobits',
    maintainer_email='',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'sherpa_server = speech_recognition_sherpa_onnx.sherpa_server:main',
            'model_downloader = speech_recognition_sherpa_onnx.model_download:main',
        ],
    },
)

from distutils.core import setup
with open("./requirements.txt") as req_file:
    requirements =[i.replace('\n', '').replace('\r', '') for i in req_file]
setup(
  name='vk-audio',         # How you named your package folder (MyLib)
  packages=['vk-audio'],   # Chose the same as "name"
  version='0.1',      # Start with a small number and increase it with every change you make
  license='MIT',
  description='Library to solve vk captcha async/sync.\nFree.\nHigh speed.',
  author='IMCorp',                   # Type in your name
  author_email='imartemy1@gmail.com', 
  url='https://github.com/imartemy1524/vk_captcha',   # Provide either the link to your github or to your website
  # download_url='https://github.com/imartemy1524/vk_captcha/archive/v_01.tar.gz',    # I explain this later on
  keywords=['vk', 'vk_api', 'captcha', 'vk_captcha', 'solver'],
  install_requires=requirements,
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
  ],
)

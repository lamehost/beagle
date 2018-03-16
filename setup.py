import uuid
from setuptools import setup,find_packages
from pip.req import parse_requirements
import codecs

import beagle as this_package

from os.path import abspath, dirname, join
here = abspath(dirname(__file__))

with codecs.open(join(here, 'README.md'), encoding='utf-8') as f:
    README = f.read()

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]

setup(
	name=this_package.__name__,
	author=this_package.__author__,
	author_email=this_package.__author_email__,
	url=this_package.__url__,
	version=this_package.__version__,
	packages=find_packages(),
	package_data={this_package.__name__: [
		'html/*'
	]},
	install_requires=reqs,
	include_package_data=True,
	entry_points={
		'console_scripts': [
			'%s = %s.cli:main' % (this_package.__name__, this_package.__name__),
		],
	},
	long_description=README,
	zip_safe=True
)

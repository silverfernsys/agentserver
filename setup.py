from setuptools import setup

# pip install --editable .

setup(
	name='AgentServer',
	version='0.1a',
	py_modules=['agentserver'],
	install_requires=[
		'backports-abc==0.4',
		'backports.ssl-match-hostname==3.5.0.1',
		'certifi==2016.2.28',
		'influxdb==2.12.0',
		'passlib==1.6.5',
		'psycopg2==2.6.1',
		'python-dateutil==2.4.2',
		'pytz==2015.7',
		'requests==2.9.1',
		'setproctitle==1.1.9',
		'singledispatch==3.4.0.3',
		'six==1.10.0',
		'SQLAlchemy==1.0.12',
		'tornado==4.3',
		'wheel==0.29.0',
	],
	entry_points='''
		[console_scripts]
		agentserver=agentserver.agentserver:main
		agentserveradmin=agentserver.agentserveradmin:main
	''',
)
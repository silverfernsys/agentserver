from cerberus import Validator

system_stats_schema = {
	'dist_name': {'type': 'string', 'required': True},
    'dist_version': {'type': 'string', 'required': True},
    'hostname': {'type': 'string', 'required': True},
    'num_cores': {'type': 'integer', 'required': True},
    'memory': {'type': 'integer', 'required': True},
    'processor': {'type': 'string', 'required': True}
}

system_stats_validator = Validator(system_stats_schema)


states_schema = {
	'group': {'type': 'string', 'required': True},
	'name': {'type': 'string', 'required': True},
	'statename': {'type': 'string', 'required': True,
		'allowed': ['STOPPED', 'STARTING', 'RUNNING',
					'BACKOFF', 'STOPPING', 'EXITED',
					'FATAL', 'UNKNOWN']},
	'pid': {'type': 'integer', 'required': True, 'nullable': True},
	'start': {'type': 'integer', 'required': True},
	'state': {'type': 'integer', 'required': True,
		'allowed': [0, 10, 20, 30, 40, 100, 200, 1000]}
}

states_validator = Validator(states_schema)


snapshot_schema = {
	'group': {'type': 'string', 'required': True},
	'name': {'type': 'string', 'required': True},
	'statename': {'type': 'string', 'required': True,
		'allowed': ['STOPPED', 'STARTING', 'RUNNING',
					'BACKOFF', 'STOPPING', 'EXITED',
					'FATAL', 'UNKNOWN']},
	'pid': {'type': 'integer', 'required': True, 'nullable': True},
	'start': {'type': 'integer', 'required': True},
	'state': {'type': 'integer', 'required': True,
		'allowed': [0, 10, 20, 30, 40, 100, 200, 1000]},
	'stats': {'type': 'list', 'required': True, 'schema':
		{'type': 'list', 'items': [{'type': 'float'}, {'type': 'float'},
			{'type': 'integer'}]}}	
}

snapshot_validator = Validator(snapshot_schema)

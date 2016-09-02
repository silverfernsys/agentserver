from json import JSONEncoder

# http://stackoverflow.com/questions/3768895/how-to-make-a-class-json-serializable
# http://stackoverflow.com/questions/18478287/making-object-json-serializable-with-regular-encoder


def _default(self, obj):
    return getattr(obj.__class__, "__json__", _default.default)(obj)

_default.default = JSONEncoder().default
JSONEncoder.default = _default

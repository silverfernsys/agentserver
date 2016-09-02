from tornado.escape import json_decode, json_encode
from tornado.web import RequestHandler


class JSONHandler(RequestHandler):
    invalid_json_error = json_encode(
        {'status': 'error', 'errors': [{'details': 'invalid json'}]})
    invalid_http_method_error = json_encode(
        {'status': 'error', 'errors': [{'details': 'invalid http method'}]})
    unknown_error = json_encode(
        {'status': 'error', 'errors': [{'details': 'unknown error'}]})
    not_authorized_error = json_encode(
        {'status': 'error', 'errors': [{'details': 'not authorized'}]})

    def error_message(self, errors):
        errors = [{'arg': k, 'details': v} for k, v in errors.items()]
        return json_encode({'status': 'error', 'errors': errors})

    def prepare(self):
        if self.request.body:
            try:
                json_data = json_decode(self.request.body)
                self.json = json_data
            except ValueError:
                # Bad Request
                self.send_error(400, message=self.invalid_json_error)

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code, **kwargs):
        if 'message' not in kwargs:
            if status_code == 405:
                kwargs['message'] = self.invalid_http_method_error
            else:
                kwargs['message'] = self.unknown_error

        self.write(kwargs['message'])

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import uuid
import redis
import string
import datetime
import logging
import hashlib
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

from typing import Optional, Dict, NoReturn, Union
from scoring import get_interests, get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad RequestMeta",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid RequestMeta",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


DATE_FORMAT = "%d.%m.%Y"


# TODO: Move descriptor's __set_name__ to this field
class Field(abc.ABC):
    def __init__(self, required=True, nullable=True):
        self.required = required
        self.nullable = nullable

    def __set_name__(self, owner, name):
        self.field_name = name
        self.model_name = owner

    @abc.abstractmethod
    def is_valid(self, value):
        return NotImplementedError


class ArgumentsField(Field):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Dict[str, Union[int, str]]):
        if not isinstance(value, dict):
            raise ValueError(f"Arguments should be dict not")


# Done [not beautiful]
class CharField(Field):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value):
        if not isinstance(value, str):
            raise ValueError("Value is not string")


# Done [not beautiful]
class EmailField(CharField):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[str]):
        if value is not None:
            if "@" not in value:
                raise Exception("Value is not an email")


# Done [not beautiful]
class PhoneField(Field):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[str]) -> NoReturn:
        if value is not None:
            if not ((len(value) == 11) | (int(value[0] == 7))):
                raise Exception("That's not not a telephone number")
            try:
                int(value)
            except:
                raise Exception("Not all symbols are digits")


# Done [not beautiful]
class FirstNameField(CharField):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[str]):
        if value is not None:
            if all([(letter in value) for letter in string.ascii_letters]):
                raise ValueError("Not a name")


# Done [not beautiful]
class LastNameField(CharField):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[str]):
        if value is not None:
            if all([(letter in value) for letter in string.ascii_letters]):
                raise ValueError("Not a last name")


# Done [not beautiful]
class DateField(Field):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[str]) -> NoReturn:
        if value is not None:
            try:
                datetime.datetime.strptime(value, DATE_FORMAT)
            except:
                raise ValueError("Value is not a date")


# Done [not beautiful]
class BirthDayField(DateField):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[str]) -> NoReturn:
        super().is_valid(value)
        date = datetime.datetime.strptime(value, DATE_FORMAT)
        age = datetime.datetime.today() - date
        if age.days / 365 > 70:
            raise ValueError("You are too old, fam")
    pass


# Done [not beautiful]
class GenderField(Field):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, value: Optional[int]):
        if value not in [0, 1]:
            raise ValueError("Must be 0 or 1")


# Done [not beautiful]
class ClientIDsField(Field):
    def __set_name__(self, owner, name):
        self.name = name

    def is_valid(self, client_id):
        if not isinstance(client_id, int):
            raise ValueError("All ids should be int")


class RequestMeta(type):
    def __new__(mcs, name, base, kwargs):
        mcs = super().__new__(mcs, name, base, kwargs)
        # TODO: Delete those fields from the kwargs, so fileds are not directly in the __init__
        mcs.fields = []
        for field_name, value in kwargs.items():
            # Not all kwargs are fields passed from Model classes - some args are maintenance:
            # __module__ and __qualname__
            # They exist in any class instance, so we can filter them out by "__"
            if ("__" in field_name) | field_name.startswith("_"):
                pass
            else:
                # TODO: Maybe we do not need making new fields variable
                setattr(mcs, field_name, value)
                mcs.fields.append(value)

        def init_for_meta_subclusses(self, **kwargs):
            for k in kwargs:
                setattr(self, k, kwargs[k])
        mcs.__init__ = init_for_meta_subclusses
        return mcs


class RequestBase(metaclass=RequestMeta):

    def _validate(self):
        for field in self.fields:
            field_name = field.name
            print("Validating field", field_name)
            try:
                field_values = getattr(self, field_name)
                if isinstance(field_values, list):
                    for field_value in field_values:
                        field.is_valid(field_value)
                else:
                    field.is_valid(field_values)
            except:
                raise ValueError("No necessary fields")
            print(f"Successfully validated {field_name}")
        print("Validation complete")
        return True


# Done
class ClientsInterestsRequest(RequestBase):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


# Done
class OnlineScoreRequest(RequestBase):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def _validate(self):
        super()._validate()
        phone_email = (getattr(self, "phone") is not None) & (getattr(self, "email") is not None)
        fname_lname = (getattr(self, "first_name") is not None) & (getattr(self, "last_name") is not None)
        gender_birthday = (getattr(self, "gender") is not None) & (getattr(self, "birthday") is not None)
        if not (phone_email | fname_lname | gender_birthday):
            raise Exception("Missing pair values (phone&email) | (fname&lname) | (gender&birthday)")


class MethodRequestMeta(metaclass=RequestMeta):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


class BaseHandler(abc.ABC):
    def __init__(self, arguments, context, store):
        self.arguments = arguments
        self.context = context
        self.store = store

    @abc.abstractmethod
    def process_request(self):
        return NotImplementedError


# Done
class ClientsInterestsHandler(BaseHandler):
    def process_request(self):
        print("PROCESS REQUEST")
        response = dict()
        cir = ClientsInterestsRequest(**self.arguments)
        cir._validate()
        client_ids = self.arguments["client_ids"]
        for client_id in client_ids:
            client_interests = get_interests(self.store, client_id)
            response[client_id] = client_interests
        self.context["nclients"] = len(client_ids)
        return response, OK


# Done
class OnlineScoreHandler(BaseHandler):
    def process_request(self):
        print("PROCESS REQUEST")
        osr = OnlineScoreRequest(**self.arguments)
        osr._validate()
        print("FAASD", self.arguments)
        return get_score(self.store, **self.arguments), OK


def method_handler(request, context, store):
    handlers = {
        "online_score": OnlineScoreHandler,
        "clients_interests": ClientsInterestsHandler
    }
    method = handlers[request["body"]["method"]]
    r = method(arguments=request["body"]["arguments"], context=context, store=store)
    response, code = r.process_request()
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = redis.Redis(db=1)  # db=1 for productions database

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            # problem here
            request = json.loads(data_string)

        except:
            code = BAD_REQUEST
        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        # self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

from enum import IntEnum, Enum


class HTTPStatus(IntEnum):
    """HTTP Status base on RFC2616
    """

    def __new__(cls, code, phrase):
        obj = int.__new__(cls, code)
        obj._value_ = code
        obj.phrase = phrase
        return obj

    @staticmethod
    def get_status_by_code(code: int):
        for status in HTTPStatus:
            if status.value == code:
                return status
        return None

    # 2xx
    OK = 200, 'OK'
    CREATED = 201, 'Created'
    ACCEPTED = 202, 'Accepted'
    NON_AUTHORITATIVE_INFORMATION = 203, 'Non Authoritative Information'
    NO_CONTENT = 204, 'No Content'
    RESET_CONTENT = 205, 'Reset Content'
    PARTIAL_CONTENT = 206, 'Partial Content'
    IM_USED = 226, 'IM Used'

    # 3xx
    MULTIPLE_CHOICES = 300, 'Multiple Choices'
    MOVED_PERMANENTLY = 301, 'Moved Permanently'
    FOUND = 302, 'Found'
    SEE_OTHER = 303, 'See Other'
    NOT_MODIFIED = 304, 'Not Modified'
    USE_PROXY_DEPRECATED = 305, 'Use Proxy Deprecated'
    UNUSED = 306, 'unused'
    TEMPORARY_REDIRECT = 307, 'Temporary Redirect'
    PERMANENT_REDIRECT = 308, 'Permanent Redirect'

    # 4xx
    BAD_REQUEST = 400, 'Bad Request'
    UNAUTHORIZED = 401, 'Unauthorized'
    # PAYMENT_REQUIRED_EXPERIMENTAL = 402, 'Payment Required Experimental'
    FORBIDDEN = 403, 'Forbidden'
    NOT_FOUND = 404, 'Not Found'
    METHOD_NOT_ALLOWED = 405, 'Method Not Allowed'
    NOT_ACCEPTABLE = 406, 'Not Acceptable'
    # PROXY_AUTHENTICATION_REQUIRED = 407, 'Proxy Authentication Required'
    REQUEST_TIMEOUT = 408, 'Request Timeout'
    CONFLICT = 409, 'Conflict'
    GONE = 410, 'Gone'
    LENGTH_REQUIRED = 411, 'Length Required'
    PRECONDITION_FAILED = 412, 'Precondition Failed'
    PAYLOAD_TOO_LARGE = 413, 'Payload Too Large'
    URI_TOO_LONG = 414, 'URI Too Long'
    UNSUPPORTED_MEDIA_TYPE = 415, 'Unsupported Media Type'
    RANGE_NOT_SATISFIABLE = 416, 'Range Not Satisfiable'
    EXPECTATION_FAILED = 417, 'Expectation Failed'
    IM_A_TEAPOT = 418, 'I\'m a teapot'
    # MISDIRECTED_REQUEST = 421, 'Misdirected Request'
    # TOO_EARLY_EXPERIMENTAL = 425, 'Too Early Experimental'
    # UPGRADE_REQUIRED = 426, 'Upgrade Required'
    PRECONDITION_REQUIRED = 428, 'Precondition Required'
    TOO_MANY_REQUESTS = 429, 'Too Many Requests'
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, 'Request Header Fields Too Large'
    UNAVAILABLE_FOR_LEGAL_REASONS = 451, 'Unavailable For Legal Reasons'

    # 5xx
    INTERNAL_SERVER_ERROR = 500, 'Internal Server Error'
    NOT_IMPLEMENTED = 501, 'Not Implemented'
    BAD_GATEWAY = 502, 'Bad Gateway'
    SERVICE_UNAVAILABLE = 503, 'Service Unavailable'
    GATEWAY_TIMEOUT = 504, 'Gateway Timeout'
    HTTP_VERSION_NOT_SUPPORTED = 505, 'HTTP Version Not Supported'
    # VARIANT_ALSO_NEGOTIATES = 506, 'Variant Also Negotiates'
    # NOT_EXTENDED = 510, 'Not Extended'
    # NETWORK_AUTHENTICATION_REQUIRED = 511, 'Network Authentication Required'


class WebError(Enum):

    def __new__(cls, code, msg):
        obj = object.__new__(Enum)
        obj._value_ = code
        obj.code = code
        obj.description = msg
        return obj

    INTERNAL_SERVER_ERROR = 'E00000', 'Internal Error'
    DEBUG_NOT_ENABLE = 'E00001', 'This endpoint is only available in debug mode'
    INVALID_IP = 'E00002', 'Invalid IP'

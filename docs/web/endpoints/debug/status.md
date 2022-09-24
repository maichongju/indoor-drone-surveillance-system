# `/debug/status/<int:code>` End Point

> :warning: This end point only available for debug purposes. Check [enable debug mode](../../README.md#enabling-debug-mode) for more information

This end point simulates a default response with the [HTTP status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) provided. The code provided must be a valid HTTP error status code (400 - 599). The program is register with the following HTTP status code:

- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `405`: Method Not Allowed
- `406`: Not Acceptable
- `408`: Request Timeout
- `409`: Conflict
- `410`: Gone
- `411`: Length Required
- `412`: Precondition Failed
- `413`: Payload Too Large
- `414`: URI Too Long
- `415`: Unsupported Media Type
- `416`: Range Not Satisfiable
- `417`: Expectation Failed
- `418`: I'm a teapot
- `428`: Precondition Required
- `429`: Too Many Requests
- `431`: Request Header Fields Too Large
- `451`: Unavailable For Legal Reasons
- `500`: Internal Server Error
- `501`: Not Implemented
- `502`: Bad Gateway
- `503`: Service Unavailable
- `504`: Gateway Timeout
- `505`: HTTP Version Not Supported

## Response

Testing default response for `404` page not found.

`url`: `/debug/status/404`

```json
{
  "status": 404,
  "error": {
    "code": "404",
    "desc": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."
  }
}
```

### Error

If an invalid HTTP status code is provided, or the HTTP status code provided is not one of the code above, a `404` error is returned.

`url`: `/debug/status/invalid` or `/debug/status/499`

Invalid HTTP status code is provided.

```json
{
    "status": 404,
    "error": {
        "code": "404",
        "desc": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."
    }
}
```

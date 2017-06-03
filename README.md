# Vincent Smoketest
## Overview
The Vincent Smoke Testing system is an automated, testing system designed to hit a series of web endpoints and test that they return expected values

Open-sourced with permission

## Domain File

The domain file is the main file, and the one used to pass to Vincent. 

It contains a list of domains, and settings about that domain. 

### Example

```
---
- domain: example.com
  endpoints: endpoints.yml
  secure: true
  session: true
  variables:
  username: some_username
  password: some_password
  example_variable_1: value
  example_variable_2: value

```

You can have one or more 'domains' in the domains file, if you want to run tests across multiple sites at once.

### Settings

* `domain` (*required*): This domain is used for the logging and to prepend to each endpoint. Do not add the protocol (e.g. http://)
    * Note: you can append part of the URL as well, if you are going to have exactly the same thing prepended to each endpoint. (e.g. `domain.com/some/prepended/url`)

* `endpoints` (*required*): The name of a the YAML file in the same directory, containing all the endpoints

* `secure` (*optional, default: `false`*): Use SSL/TLS

* `session` (*optional, default: `false`*): Persists cookies and a session for each request?

    * Note: Cookies only last for a single domain. When the test starts the next domain, the cookies are reset (so you can't do cross-domain login testing, for example)

* **Variables** (*optional*): Any global variables to substitute into the `endpoints.yml` file (below)

 

## Endpoints File

The endpoints file contains details about each endpoint, how to interact with it, and what to expect from each endpoint

### Example
```
---

##
# Log in
##
- description: Capture CSRF Tokens
  url: /auth/login
  method: get  
  # Designed for capturing the values of form fields (specifically) for the purpose of later substitution; designed
  # for use with CSRF
  capture: 
    - name: TokenFields
      mode: html
      path: //input[@name='csrf[fields]']/@value
    - name: TokenKey
      mode: html
      path: //input[@name='csrf[key]']/@value
- description: Log us in
  url: /auth/login
  method: post
  data:
    mode: form
    body: >
      {
        "_method": "POST",
        "user[username]": "%username%",
        "user[password]": "%password%",
        "user[remember_me]": "0",
        "csrf[fields]": "%TokenFields%",
        "csrf[key]": "%TokenKey%",
      }
  options:
    allow_redirects: true
  expected:
    code: 200
    contains: Dashboard
    url: .*?/(user/dashboard)?(?:\?([a-z0-9]+\=.+?&?)*)?$
    stop_on_fail: true
- description: Switch to an active project
  url: /projects/select/%example_variable%
  method: get
  options:
    allow_redirects: true
  expected:
    code: 200
    contains: Dashboard
```

### Settings


* `description` (*optional*): Just a human readable description. Ignored by Vincent

* `url` (*required*): The URL endpoint, including any GET variables

* `method` (*optional, default: `get`*): The HTTP method to use
    * Must be in lowercase
    * No explicit options are enforced, but if an invalid HTTP method is chosen, the program may fail

* `capture` (*optional*): See **Variable Capture** (below)

* `data` (*optional*): Data for the request body (e.g. a `post` or `put`)

    * `data.mode` (*optional, default: `raw`*):
        * `raw`: Send the data as a raw payload
        * `form`: Form-encode the data from a JSON-array
    * `data.body` (*required, if `data` defined*): Response body to send to server
        * YAML requires a single right-angle bracket (`>`) followed by a newline if sending multiline
        * Data body has **Variable Substitution** applied (see below)

* `options` (*optional*)
    * A series of optional overrides about the request

    * `options.allow_redirects` (*optional, default: `false`*): Follow 3xx requests automatically to their destination


* `expected` (*optional*): Check what the response contained

    * `expected.stop_on_fail` (*optional, default: `false`*): Stops testing if the **Response Expectations** fail
    * `expected.code` (*optional*): Check response code
    * `expected.contains` (*optional*): Check response body contains certain text
        * This is a regex string; you must escape any regex characters you want to check literally (e.g. periods)
    * `expected.encoding` (*optional*): Check `content-encoding` header
    * `expected.validate_format` (*optional*): Attempt to parse the format, and throw an error if parsing fails
        * Currently only supports `json` as an option
    * `expected.url` (*optional*): The destination URL we should be on after making the request
        * If `allow_redirects` is on, this is the final destination URL after following all redirects
        * This is a regex string; you must escape any regex characters you want to check literally (e.g. periods)


## Variable Capture and Substitution

Sometimes you need to capture variables for subsequent requests - e.g. CSRF tokens.

### Variable Substitution
Variable substitution takes place in the URL (before the request is run) and the POST payload. 

To substitute a variable, simply put `%variablename%` into the payload/url and it will be substituted. 

**NOTE WELL**: Variable Substitution is DUMB
Seriously, it's dumb. There is no way to escape the percentage symbol, if you DON'T want to substitute a variable in a particular body of text

However, Vincent will only substitute a defined variable; a missing variable will be ignored.

E.g. if `%sometext% `exists in the body, and `sometext` is not a defined variable, then `%sometext%` won't be replaced.

 

### Defining Variables
There are two ways of defining variables. 

### Domains File
The 'key' in the YAML file will act as the variable name.

```
    [...]
    variables:
        username: SomeUsername
        password: SomePassword
        example_variable_1: 12346
```
So now you can call %username%, %password% and %example_variable_1% in your payload/URL

#### Variable Capture
The other way is to explicitly capture the variable:

```
[...]
capture:
- name: TokenFields
  mode: html
  path: //input[@name='csrf[fields]']/@value
```

* `name` (*optional*): The name of the variable to define, for later substitution (in this case, `%TokenFields%`)
    * If a name isn't defined, then the first non-named variable captured will be variable 1 (ie, substituted with `%1%`), 2 (`%2%`) and so on. 
    * This does not persist across endpoints - if you capture a non-named variable once (so it's stored in `1`), then do it again on another endpoint, it will overwrite the previous value (because it also tries to store in 1)
    * If a variable is named that was previously defined (e.g. in a previous endpoint call, or in the domains file) it will be overwritten

* `mode` (*optional, default: `html`*): The capture mode to use (which dictates how the `path` parameter operates).
    * Only supports `html`

* `path` (*required*): The path of the data to capture - e.g. an XPath. The value found here will be stored in the variable.

    * If multiple elements are found for the Path (e.g, if you were to do //div to capture all divs), they will all be added into the variable as a list. The behaviour of this, if substituting, is currently undefined.

 

## Running Vincent
Here are the runtime arguments available to use Vincent:

```
usage: smoketest.py [-h] [-q] [--loglevel LEVEL] [--version] sites
    Smoke test a series of web endpoints
    positional arguments:
    sites Name of sites YAML file to load
    optional arguments:
    -h, --help show this help message and exit
    -q, --quiet Only show site-level pass/fails
    --loglevel LEVEL Log level (higher is more verbose). Overrides --quiet
    --version Program version
```

Vincent returns a non-zero response code if any of the domains it's testing throws a FAIL for any reason (basically it just there to tell you there's 'Smoke').

### Libraries
Vincent requires Python2.7 and the following non-standard libraries:

* pyyaml
* lxml
* requests
* argparse



# Extending Vincent
### New Expectations/Assertions

If you wish to extend Vincent with new 'expectations' (e.g. if you wish to start validating the headers, for example), then you can add/modify the assertion as a new function in SmokeAssertions at the top of `smoke-test.py`

Once done, look for the line "if 'expected' in endpoint". In this section, you will see how to call your new assertion; copy a line as appropriate, to add the new assertion.

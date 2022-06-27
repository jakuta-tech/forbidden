#!/usr/bin/env python3

import datetime
import sys
import urllib.parse
import os
import shutil
import re
import concurrent.futures
import subprocess
import io
import pycurl
import termcolor
import json

start = datetime.datetime.now()

# -------------------------- INFO --------------------------

def basic():
	global proceed
	proceed = False
	print("Stresser v2.8 ( github.com/ivan-sincek/forbidden )")
	print("")
	print("Usage:   python3 stresser.py -u url                        -dir directory -r repeat -th threads [-f force] [-o out         ]")
	print("Example: python3 stresser.py -u https://example.com/secret -dir results   -r 1000   -th 200     [-f GET  ] [-o results.json]")

def advanced():
	basic()
	print("")
	print("DESCRIPTION")
	print("    Bypass 4xx HTTP response status codes with stress testing")
	print("URL")
	print("    Inaccessible or forbidden URL")
	print("    Parameters and fragments are ignored")
	print("    -u <url> - https://example.com/secret | etc.")
	print("DIRECTORY")
	print("    Output directory")
	print("    All valid and unique HTTP responses will be saved in this directory")
	print("    -dir <directory> - results | etc.")
	print("REPEAT")
	print("    Number of HTTP requests to send for each test case")
	print("    -r <repeat> - 1000 | etc.")
	print("THREADS")
	print("    Number of parallel threads to run")
	print("    -th <threads> - 200 | etc.")
	print("FORCE")
	print("    Force an HTTP method for nonspecific test cases")
	print("    -f <force> - GET | POST | CUSTOM | etc.")
	print("IGNORE")
	print("    Filter out 200 OK false positive results by text")
	print("    Spacing will be stripped")
	print("    -i <ignore> - Forbidden | \"Access Denied\" | etc.")
	print("LENGTHS")
	print("    Filter out 200 OK false positive results by content lengths")
	print("    Specify 'base' to ignore content length of base HTTP response")
	print("    Use comma separated values")
	print("    -l <lengths> - 12 | base | etc.")
	print("AGENT")
	print("    User agent to use")
	print("    Default: Stresser/2.8")
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

def parse_content_lengths(value, specials):
	tmp = []
	array = value.split(",")
	for entry in array:
		entry = entry.strip()
		if entry:
			if entry in specials: # base
				tmp.append(entry)
			elif entry.isdigit() and int(entry) >= 0:
				tmp.append(int(entry))
			else:
				tmp = []
				break
	return unique(tmp)

def remove_directory(directory):
	removed = True
	try:
		if os.path.exists(directory):
			shutil.rmtree(directory)
	except Exception:
		removed = False
		print(("Cannot remove '{0}' directory").format(directory))
	return removed

def create_directory(directory):
	created = True
	try:
		if not os.path.exists(directory):
			os.mkdir(directory)
	except Exception:
		created = False
		print(("Cannot create '{0}' directory").format(directory))
	return created

def check_directory(directory):
	success = False
	overwrite = "yes"
	if os.path.exists(directory):
		print(("'{0}' directory already exists").format(directory))
		overwrite = input("Overwrite the output directory (yes): ").lower()
	if overwrite == "yes" and remove_directory(directory):
		success = create_directory(directory)
	return success

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

args = {"url": None, "directory": None, "repeat": None, "threads": None, "force": None, "ignore": None, "lengths": None, "agent": None, "proxy": None, "out": None}

# TO DO: Better URL validation. Validate "proxy".
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
		elif key == "-dir" and args["directory"] is None:
			args["directory"] = os.path.abspath(value)
		elif key == "-r" and args["repeat"] is None:
			args["repeat"] = value
			if not args["repeat"].isdigit():
				error("Number of HTTP requests must be numeric")
			else:
				args["repeat"] = int(args["repeat"])
				if args["repeat"] < 1:
					error("Number of HTTP requests must be greater than zero")
		elif key == "-th" and args["threads"] is None:
			args["threads"] = value
			if not args["threads"].isdigit():
				error("Number of parallel threads must be numeric")
			else:
				args["threads"] = int(args["threads"])
				if args["threads"] < 1:
					error("Number of parallel threads must be greater than zero")
		elif key == "-f" and args["force"] is None:
			args["force"] = value.upper()
		elif key == "-i" and args["ignore"] is None:
			args["ignore"] = value
		elif key == "-l" and args["lengths"] is None:
			args["lengths"] = parse_content_lengths(value.lower(), ["base"])
			if not args["lengths"]:
				error("Content length must be either 'base' or numeric and equal or greater than zero")
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
	if args["url"] is None or args["directory"] is None or args["repeat"] is None or args["threads"] is None or not check(argc, args):
		error("Missing a mandatory option (-u, -dir, -r, -th) and/or optional (-f, -i, -l, -a, -x, -o)", True)
else:
	error("Incorrect usage", True)

# --------------------- VALIDATION END ---------------------

# ------------------- TEST RECORDS BEGIN -------------------

def record(raw, identifier, url, method, headers, body, ignore, agent, proxy):
	return {"raw": raw, "id": identifier, "url": url, "method": method, "headers": headers, "body": body, "ignore": ignore, "agent": agent, "proxy": proxy, "command": None, "code": 0, "length": 0}

def get_records(identifier, append, repeat, urls, methods, headers = None, body = None, ignore = None, agent = None, proxy = None):
	if not isinstance(urls, list):
		urls = [urls]
	records = []
	if headers:
		for url in urls:
			for method in methods:
				for header in headers:
					identifier += 1
					for i in range(repeat):
						records.append(record(identifier, str(identifier) + append.upper(), url, method, header if isinstance(header, list) else [header], body, ignore, agent, proxy))
	else:
		for url in urls:
			for method in methods:
				identifier += 1
				for i in range(repeat):
					records.append(record(identifier, str(identifier) + append.upper(), url, method, [], body, ignore, agent, proxy))
	return records

def fetch(url, method, headers = None, body = None, ignore = None, agent = None, proxy = None):
	return run_curl(record(0, "-FETCH-0", url, method, headers, body, ignore, agent, proxy))

# -------------------- TEST RECORDS END --------------------

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

def get_collection(url, repeat, force = None, ignore = None, agent = None, proxy = None):
	collection = []
	identifier = 0
	local = {
		"methods": [force] if force else ["GET"]
	}
	# NOTE: Stress testing.
	records = get_records(identifier, "-STRESS-1", repeat, url["full"], local["methods"], None, None, ignore, agent, proxy)
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

def get_timestamp(text):
	return print(("{0} - {1}").format(datetime.datetime.now().strftime("%H:%M:%S"), text))

def progress(count, total):
	end = "\r"
	if count == total:
		end = "\n"
	print(("Progress: {0}/{1} | {2:.2f}%").format(count, total, (count / total) * 100), end = end)

def run_curl(record):
	encoding = "UTF-8"
	response = io.BytesIO()
	curl = pycurl.Curl()
	curl.setopt(pycurl.CONNECTTIMEOUT, 90)
	curl.setopt(pycurl.TIMEOUT, 180)
	curl.setopt(pycurl.VERBOSE, False)
	curl.setopt(pycurl.SSL_VERIFYPEER, False)
	curl.setopt(pycurl.SSL_VERIFYHOST, False)
	curl.setopt(pycurl.FOLLOWLOCATION, True)
	curl.setopt(pycurl.MAXREDIRS, 10)
	curl.setopt(pycurl.PATH_AS_IS, True)
	if record["body"]:
		curl.setopt(pycurl.POSTFIELDS, record["body"].encode(encoding))
	if record["headers"]:
		curl.setopt(pycurl.HTTPHEADER, [header.encode(encoding) for header in record["headers"]])
	if record["agent"]:
		curl.setopt(pycurl.USERAGENT, record["agent"].encode(encoding))
	if record["proxy"]:
		curl.setopt(pycurl.PROXY, record["proxy"].encode(encoding))
	curl.setopt(pycurl.CUSTOMREQUEST, record["method"])
	curl.setopt(pycurl.URL, record["url"].encode(encoding))
	curl.setopt(pycurl.WRITEDATA, response)
	try:
		curl.perform()
		record["code"] = int(curl.getinfo(pycurl.RESPONSE_CODE))
		record["length"] = int(curl.getinfo(pycurl.SIZE_DOWNLOAD))
		data = response.getvalue().decode("ISO-8859-1")
		if record["ignore"] and (record["ignore"]["text"] and re.search(record["ignore"]["text"], data, re.IGNORECASE) or record["ignore"]["lengths"] and any(record["length"] == length for length in record["ignore"]["lengths"])):
			record["code"] = 0
		record["id"] = ("{0}-{1}-{2}").format(record["id"], record["code"], record["length"])
		file = ("{0}.txt").format(record["id"])
		# NOTE: Additional validation to prevent congestion from writing large and usless data to files.
		if record["code"] >= 200 and record["code"] < 400 and not os.path.exists(file):
			open(file, "w").write(data)
	except pycurl.error:
		pass
	finally:
		response.close()
		curl.close()
	return record

def filter(collection):
	tmp = []
	ids = []
	for record in collection:
		if record["id"] not in ids:
			ids.append(record["id"])
			tmp.append(record)
	return tmp

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
	results = filter(results)
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

def bypass(collection, threads = 5):
	results = []
	count = 0
	total = len(collection)
	print(("Number of created test records: {0}").format(total))
	get_timestamp("Running tests...")
	progress(count, total)
	with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
		subprocesses = {executor.submit(run_curl, record): record for record in collection}
		for subprocess in concurrent.futures.as_completed(subprocesses):
			results.append(subprocess.result())
			count += 1
			progress(count, total)
	return results

if proceed and check_directory(args["directory"]):
	os.chdir(args["directory"])
	print("#######################################################################")
	print("#                                                                     #")
	print("#                            Stresser v2.8                            #")
	print("#                                by Ivan Sincek                       #")
	print("#                                                                     #")
	print("# Bypass 4xx HTTP response status codes with stress testing.          #")
	print("# GitHub repository at github.com/ivan-sincek/forbidden.              #")
	print("# Feel free to donate bitcoin at 1BrZM6T7G9RN8vbabnfXu4M6Lpgztq6Y14.  #")
	print("#                                                                     #")
	print("#######################################################################")
	# --------------------
	if not args["agent"]:
		args["agent"] = "Stresser/2.8"
	# --------------------
	url = parse_url(args["url"])
	ignore = {"text": args["ignore"], "lengths": args["lengths"] if args["lengths"] else []}
	# --------------------
	# NOTE: Fetch content length of base HTTP response.
	if "base" in ignore["lengths"]:
		ignore["lengths"].append(fetch(url["full"], args["force"] if args["force"] else "GET", None, None, None, args["agent"], None)["length"])
		ignore["lengths"].pop(ignore["lengths"].index("base"))
	# --------------------
	collection = get_collection(url, args["repeat"], args["force"], ignore, args["agent"], args["proxy"])
	if not collection:
		print("No test records were created")
		remove_directory(args["directory"])
	else:
		results = parse_results(bypass(get_commands(collection), args["threads"]))
		if not results:
			print("No result matched the validation criteria")
			remove_directory(args["directory"])
		else:
			print(("Number of valid results: {0}").format(len(results)))
			if args["out"]:
				write_file(jdump(results), args["out"])
	print(("Script has finished in {0}").format(datetime.datetime.now() - start))

# ------------------------ TASK END ------------------------

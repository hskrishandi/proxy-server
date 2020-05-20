from socket import *
import threading
import os

server_port = 12345
server_socket = socket(AF_INET,SOCK_STREAM)
server_socket.bind(('',server_port))
server_socket.listen(1)

blocked = ['sing.cse.ust.hk', 'www.google.com']
cache = dict()
print('The server is ready to receive')

def get_request_details(request):
	splitted = request.split('\n')
	first_line = splitted[0]
	second_line = splitted[1]

	first_line = first_line.split()
	
	method = first_line[0]
	url = first_line[1]
	host = second_line.split()[1]

	pos = url.find(host)
	relative_url = url[(pos + len(host)):]

	return { 
		"method": method,
		"host": host,
		"url": url,
		"relative_url": relative_url
	}

def convert_request(request, url, relative_url):
	request = request.replace(url, relative_url, 1)
	request = request.replace("Proxy-Connection:", "Connection:")

	return request

def process_filename(filename):
	if filename[:4] == "www.":
		filename = filename[4:]
	
	if filename[-1] == "/":
		filename += "index.html"

	filename = "cache/" + filename

	return filename

def check_cache(filename):
	if filename in cache:
		return True
	else:
		return False

def fetch_from_cache(filename, client_socket):
	data = cache[filename]
	client_socket.sendall(data)

def store_to_cache(filename, data):
	filename = process_filename(filename)
	cache[filename] = data

def make_http_request(host, request, client_socket):
	port = 80
	proxy_client = socket(AF_INET, SOCK_STREAM)
	proxy_client.connect((host, port))
	proxy_client.send(request)
	proxy_client.settimeout(10)

	receive = proxy_client.recv(4096)
	data = ''

	try:
		while len(receive):
			client_socket.sendall(receive)
			data += receive
			receive = proxy_client.recv(4096)
	except:
		pass
	
	proxy_client.close()
	return data

def make_https_request(host, request, client_socket):
	port = 443
	host = host.split(':')[0]
	proxy_client = socket(AF_INET, SOCK_STREAM)
	proxy_client.connect((host, port))

	connect_response = 'HTTP/1.1 200 Connection Established\r\n\r\n'
	client_socket.send(connect_response.encode())

	client_socket.setblocking(0)
	proxy_client.setblocking(0)

	while True:
		try:
			request = client_socket.recv(4096)
			proxy_client.sendall(request)
		except:
			pass

		try:
			response = proxy_client.recv(4096)
			client_socket.sendall(response)
		except:
			pass
	
def proxy_thread(client_socket, client_address):
	print("called")
	request = client_socket.recv(4096)
	if not request or request == '':
		return
	
	details = get_request_details(request)

	if details["host"] in blocked:
		print("Blocked: ", details["host"])
		error_response = 'HTTP/1.1 404 Not Found\r\n\r\n'
		client_socket.sendall(error_response.encode())
		client_socket.close()
		return

	if details["method"] == 'CONNECT':
		print("https connection:", details["url"])
		make_https_request(details["url"], request, client_socket)
		client_socket.close()
		return

	cache_filename = process_filename(details["host"] + details["relative_url"])
	cached_before = check_cache(cache_filename)

	if cached_before:
		print("Getting from cache:", details["url"])
		fetch_from_cache(cache_filename, client_socket)
	else:
		print("New request:", details["url"])
		request = convert_request(request, details["url"], details["relative_url"])
		data = make_http_request(details["host"], request, client_socket)
		store_to_cache(details["host"] + details["relative_url"], data)

	client_socket.close()
	print("Closed:", details["url"])

while 1:
	client_socket, client_address = server_socket.accept()
	d = threading.Thread(
		name=str(client_address),
		target=proxy_thread,
		args=(client_socket, client_address)
	)
	d.setDaemon(True)
	d.start()



	
	

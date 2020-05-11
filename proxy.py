from socket import *
import threading
import os

server_port = 12345
server_socket = socket(AF_INET,SOCK_STREAM)
server_socket.bind(('',server_port))
server_socket.listen(1)
print('The server is ready to receive')

def get_url_info(request):
	splitted = request.split('\n')
	first_line = splitted[0]
	second_line = splitted[1]

	url = first_line.split()[1]
	host = second_line.split()[1]

	pos = url.find(host)
	relative_url = url[(pos + len(host)):]

	return host, url, relative_url

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

def fetch_from_cache(filename):
	filename = process_filename(filename)

	try:
		f = open(filename)
		content = f.read()
		f.close()
		return content
	except IOError:
		return None

def store_to_cache(filename, data):
	filename = process_filename(filename)
	print("Storing to cache: ", filename)
	if not os.path.exists(os.path.dirname(filename)):
		try:
			os.makedirs(os.path.dirname(filename))
		except OSError as exc: # Guard against race condition
			if exc.errno != errno.EEXIST:
				raise
	f = open(filename, "w")
	f.write(data)
	f.close()

def make_request(host, request, client_socket):
	port = 80
	proxy_client = socket(AF_INET, SOCK_STREAM)
	proxy_client.connect((host, port))
	proxy_client.send(request)

	receive = proxy_client.recv(1024)
	data = receive
	while len(receive):
		client_socket.sendall(receive)
		data += receive
		receive = proxy_client.recv(1024)
	proxy_client.close()
	return data

def proxy_thread(client_socket, client_address):
	request = client_socket.recv(1024)
	if not request or request == '':
		return
	print(request)
	host, url, relative_url = get_url_info(request)

	content = fetch_from_cache(host + relative_url)
	if content:
		print("Getting from cache:", url)
		client_socket.sendall(content)
	else:
		print("New request:", url)
		request = convert_request(request, url, relative_url)
		data = make_request(host, request, client_socket)
		store_to_cache(host + relative_url, data)

	client_socket.close()

while 1:
	client_socket, client_address = server_socket.accept()
	print(client_socket, client_address)
	d = threading.Thread(
		target=proxy_thread,
		args=(client_socket, client_address)
	)
	d.setDaemon(True)
	d.start()






	
	

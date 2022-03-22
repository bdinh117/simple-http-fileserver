#!/usr/bin/env python3

import socket
import sys
import datetime
import os
import select
import queue

from file_reader import FileReader


MY_HEADERS = ["Date", "Content-Type", "Content-Length","Server"]

class Jewel:

    # Note, this starter example of using the socket is very simple and
    # insufficient for implementing the project. You will have to modify this
    # code.
    def __init__(self, port, file_path, file_reader):
        self.file_path = file_path.replace("\\","/") #convert all slashes to same direction
        self.file_reader = file_reader


        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", port)) #associate the socket with a specific port



        s.listen(5) #Enable a server to accept connections.
        # backlog arg ,"number of unaccepted connections that the system will allow before refusing new connections"
        #queue size for pending connections



        maybe_readable =[s] #list of sockets that could become readable (have stuff to read when we call recv)(see when our initial server sock contains something to read)
        maybe_writable = [] #list of sockets that could become writable (able to send stuff to it)
        maybe_error= [] #sockets with errors?

        inbox= {}#store responses for requests in here, so we can send them to the right socket later when (it becomes writable)


        while True:
            # select monitors these input lists of sockets, and tell us when sockets become readable,writeable,or have errors
            ready_to_read_from, ready_to_write_to, in_error = select.select(maybe_readable, maybe_writable, maybe_error)

            # print(f"ie{len(in_error)}",f"rr{len(ready_to_read_from)}",f"rw{len(ready_to_write_to)}",f"mr{len(maybe_readable)}")

            #---------READ NEW STUFF FROM READABLE SOCKS---------
            for sock in ready_to_read_from:
                if sock is s:#if server, means there is incoming connection, from another client.  ?
                    (client, address) = s.accept()  # accept(), blocks execution and waits for an incoming connection.
                    print(f"[CONN] Connection from {address[0]} on port {address[1]}")
                    # when a client connects, it returns a socket object (client), and the address of the client.
                    # use this new socket object, to communicate with client.

                    maybe_readable.append(client) #want to read requests from this sock in the future.
                else:#else is a client
                    data = sock.recv(1024)
                    # print(data)
                    # if return an empty bytes object b'' , client has closed the connection
                    if not data:#client closed the connection. erase all traces of this client
                        if(sock in maybe_readable):
                            maybe_readable.remove(sock)
                        if(sock in maybe_writable):
                            maybe_writable.remove(sock)
                        del inbox[sock]
                        sock.close()

                        continue
                    if sock not in maybe_writable:#if not already checking writability for this sock
                        maybe_writable.append(sock) #want to send back a response to its request, when it becomes writable

                    #STORE THE RESPONSE TO IT, WHICH we'll send to this client when it becomes writable
                    data = data.decode("utf-8")
                    method, path = self.parse_request(data)
                    addr = sock.getpeername() #addr[0] is ip. 1 is port. of the remote socket
                    print(f"[REQU] [{addr[0]}:{addr[1]}] {method} request for {path}")
                    response, err = self.form_response(method, path)
                    if(err == 400):
                        print(f"[ERRO] [{addr[0]}:{addr[1]}] request returned error {err}")
                    elif(err):
                        print(f"[ERRO] [{addr[0]}:{addr[1]}] {method} request returned error {err}")

                    #QUEUE IT UP
                    #if sock already has msg queue
                    if(sock in inbox):
                        inbox[sock].put(response)
                    else:#create new queue
                        fifo = queue.Queue()
                        fifo.put(response)
                        inbox[sock] = fifo
                ready_to_read_from.remove(sock) #we've read the sock. done with it.

            for sock in ready_to_write_to:
                if(not inbox[sock].empty()):
                    #send responses 1 at a time. bc client may become unwritable after. wait for it to become writable agian
                    resp = inbox[sock].get_nowait()#non blocking version
                    # print(resp)
                    sock.send(resp)
                    ready_to_write_to.remove(sock)
                else:
                    maybe_writable.remove(sock)#no more messages to write so dont care about when sock becomes writable.
            for sock in in_error:#nuke the sock, if someting wrong with it.
                if (sock in maybe_readable):
                    maybe_readable.remove(sock)
                if (sock in maybe_writable):
                    maybe_writable.remove(sock)
                #del inbox[sock]
                sock.close()


    #given data in string from socket. returns the method and file path of it.
    def parse_request(self,request):
        try:
            request = request.split("\r\n")[:-2]#last two will be blanks, bc header ends in \r\n\r\n. ignore those
            # print(request)
            requestLine = request[0] #only need the first line. which consists of method and filepath
            headers = request[1:]

            requestLine = requestLine.split()
            method = requestLine[0]
            path = requestLine[1]
            return method, path
        except:
            return None, None


    #determine a response to send. based on the mathod (get or head). find the specified file as well.
    #response will consist of status line, headers, and possible file .
    def form_response(self,method, object):
        response = ""
        err = ""#return err code for logging
        status = "HTTP/1.1 200 OK"
        headers = dict.fromkeys(MY_HEADERS)
        headers["Date"] = datetime.datetime.today().strftime("%a, %d %b %Y %H:%M:%S")  # strftime.org
        headers["Server"] = "bd4jqg'sCoolServer"

        file=b''

        if (method == "HEAD" or method == "GET"):
            p = self.file_path + object  # full path to file.
            if (method == "GET"):
                f = self.file_reader.get(p)#try to get file/directory
                if not f:
                    status = "HTTP/1.1 404 Not Found"
                    err = 404
                else:
                    file = f

            #CONTENT LENGTH HEADER
            size = self.file_reader.head(p)#COULD RAISE FILE NOT FOUND ERROR
            if(size is not None):#if there exists file/dir
                headers["Content-Length"] = str(size)
                # CONTENT TYPE HEADER
                name, extension = os.path.splitext(object)
                ext = extension[1:]

                if (ext == "html" or ext == "css"):
                    headers["Content-Type"] = f"text/{ext}"
                elif (ext == "png" or ext == "jpeg" or ext == "gif" or ext == "jpg"):
                    headers["Content-Type"] = f"image/{ext}"
                elif(ext == ""):#case when path is a directory. so we returned a html file in that case.
                    headers["Content-Type"] = f"text/html"
            else:
                status = "HTTP/1.1 404 Not Found"
                err = 404
        elif(method is None or object is None):
            status ="HTTP/1.1 400 Bad Request"
            err = 400
        else:
            status = "HTTP/1.1 501 Method Unimplemented"
            err = 501

        if (err):
            headers["Content-Length"] = "0"

        part1 = f"{status}\r\n"#status line
        part2 =""#headers
        for head, val in headers.items():
            if(val):#not none
                part2+=f"{head}: {val}\r\n"
        part2+="\r\n" #end headers

        response = part1.encode('utf-8') + part2.encode('utf-8') + file


        return response, err

if __name__ == "__main__":
    port = int(sys.argv[1])
    file_path = sys.argv[2]

    FR = FileReader()

    J = Jewel(port, file_path, FR)

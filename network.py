import time
import socket
import select
import threading
import Queue
import sys

class HostHandle(object):
    def __init__(self, name):
        self.sockets = {}
        self.names = [name]
        
        self.sendto = Queue.Queue()
        
    def accept(self, client):
        client.send('@@AcceptRequest')
        
    def disconnect(self, socket, clients, recieved):
        if socket in self.sockets.keys():            
            data = '%s has left' % (self.sockets[socket])
        else:
            data = 'Someone has left'
            
        for sock in clients.iterkeys():
            if sock != socket:
                clients[sock].send(data)
        recieved.put(data)
        recieved.task_done()
        
    def data_check(self, socket, data, clients, recieved):
        if data.startswith('@@'):
            d = data.split()
            if data.startswith('@@PlayerName'):
                self.sockets[socket] = d[1]
                self.names.append(d[1])
                players = '@@Players'
                for n in self.names:
                    players += ' ' + n                                    
                    
                for sock in clients.iterkeys():
                    if sock != socket:
                        clients[sock].send(data)
                        clients[sock].send(d[1] + ' has joined')
                        
                recieved.put(d[1] + ' has joined')
                recieved.task_done()
                
            return True
        return False
        
class ClientHandle(object):
    def __init__(self, name):
        self.name = name
        self.names = []
        
    def data_check(self, data, qsend):
        if data.startswith('@@'):
            d = data.split()
            if data.startswith('@@AcceptRequest'):
                qsend.put('@@PlayerName %s' % (self.name))
                qsend.task_done()
            elif data.startswith('@@Players'):
                self.names = d[1:]
                    
            return True
        return False
        
class ClientObject(object):
    def __init__(self):
        self.data = Queue.Queue()
        
    def send(self, data):
        self.data.put(data)
        self.data.task_done()
        
    def get(self):
        if self.data.empty():
            return None
        return self.data.get()

# ----- ----- ----- ----- ----- --*-- ----- ----- ----- ----- ----- #
#                            Host Server                            #
# ----- ----- ----- ----- ----- --*-- ----- ----- ----- ----- ----- #
class HostServer(threading.Thread):
    def __init__(self, host, port, name, handle=None):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(9)
        self.sock_list = [self.sock]
        if handle:
            self.handle = handle
        else:
            self.handle = HostHandle(name)

        self.running = True
        
        self.clients = {}
        self.recieved = Queue.Queue()

    def run(self):
        self.running = True
        while self.running:
            sread, swrite, serror = select.select(self.sock_list, self.sock_list, [], 0)

            for read_socket in sread:

                if read_socket == self.sock:
                    sockfd, addr = read_socket.accept()
                    self.sock_list.append(sockfd)
                    client = ClientObject()
                    self.clients[sockfd] = client
                    self.handle.accept(client)
                else:
                    try:
                        data = read_socket.recv(4096)
                        if data:
                            if self.handle.data_check(read_socket, data, self.clients, self.recieved):
                                pass
                            else:
                                # broadcast
                                for socket in self.sock_list:
                                    if socket != self.sock and socket != read_socket:
                                        self.clients[socket].send(data)
                                self.recieved.put(data)
                                self.recieved.task_done()
                        else:
                            self.handle.disconnect(read_socket, self.clients, self.recieved)
                            if read_socket in self.sock_list:
                                self.sock_list.remove(read_socket)
                                del self.clients[read_socket]
                    except:
                        self.handle.disconnect(read_socket, self.clients, self.recieved)
                        if read_socket in self.sock_list:
                            self.sock_list.remove(read_socket)
                            del self.clients[read_socket]
                        continue
                        
            for write_socket in swrite:
                if write_socket != self.sock and write_socket in self.sock_list:
                    data = self.clients[write_socket].get()
                    if data:
                        self.send_data(write_socket, data)

            time.sleep(0.04)

        self.sock.close()
        
    def send_data(self, socket, data):
        try:
            socket.send(data)
        except:
            self.handle.disconnect(socket, self.clients, self.recieved)
            socket.close()
            if socket in self.sock_list:
                self.sock_list.remove(socket)
                del self.clients[socket]

    def stop(self):
        self.recieved.join()
        self.running = False

    def get(self):
        if self.recieved.empty():
            return None

        return self.recieved.get()

    def send(self, data):
        for socket in self.sock_list:
            if socket != self.sock:
                self.clients[socket].send(data)

# ----- ----- ----- ----- ----- --*-- ----- ----- ----- ----- ----- #
#                               Client                              #
# ----- ----- ----- ----- ----- --*-- ----- ----- ----- ----- ----- #
class Client(threading.Thread):
    def __init__(self, host, port, name, handle=None):
        threading.Thread.__init__(self)

        self.recv_queue = Queue.Queue()
        self.send_queue = Queue.Queue()        

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock_list = [self.sock]

        try:
            self.sock.connect((host, port))
            self.running = True
        except:
            self.running = False
            
        if handle:
            self.handle = handle
        else:
            self.handle = ClientHandle(name)

    def run(self):
        while self.running:
            sread, swrite, serror = select.select(self.sock_list, self.sock_list, [], 0)

            for socket in sread:

                if socket == self.sock:
                    data = socket.recv(4096)
                    if data:
                        if self.handle.data_check(data, self.send_queue):
                            pass
                        else:
                            self.recv_queue.put(data)
                            self.recv_queue.task_done()
                    else:
                        self.recv_queue.put('Chat room has close')
                        self.recv_queue.task_done()
                        self.running = False

            for socket in swrite:
                if not self.send_queue.empty():

                    data = self.send_queue.get()
                    socket.send(data)

            time.sleep(0.04)

        self.sock.close()

    def stop(self):
        self.recv_queue.join()
        self.send_queue.join()
        self.running = False

    def get(self):
        if self.recv_queue.empty():
            return None

        return self.recv_queue.get()

    def send(self, data):
        self.send_queue.put(data)
        self.send_queue.task_done()

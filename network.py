import tcp_network
import Queue

class Structure(object):
    pass

class Chatter(object):
    def __init__(self):
        self.queue = Queue.Queue()
        
    def send(self, data):
        self.queue.put(data)        

    def get(self, function):
        if not self.queue.empty():
            function(self.queue.get())
            self.queue.task_done()

class chat_engine(object):
    socket_names = {}
    users = {}
    name = ""
    connection = Structure()
    connection.stream = None
    connection.host = False

class Host(tcp_network.Server):
    def __init__(self, host='0.0.0.0', port=9012):
        tcp_network.Server.__init__(self, host, port, 10)
        self.recieved = Queue.Queue()
        self.waiting_chattername = {}
        
    def accepting(self, socket):
        chatter = Chatter()
        chatter.send('@@Accept NoData')
        self.waiting_chattername[socket] = chatter
        
    def recieving(self, socket, data):
        if data.startswith('@@'):
            d = data.split()
            if data.startswith('@@Name'):
                name = d[1]
                chat_engine.socket_names[socket] = name
                chat_engine.users[name] = self.waiting_chattername[socket]
                del self.waiting_chattername[socket]
                names = [chat_engine.socket_names[p] for p in self.socket_list if p != self.sock]
                names = [chat_engine.name] + names
                chat_engine.users[name].send("#Names " + ' '.join(names))
                self.broadcast(socket, '#User ' + name)
        else:
            self.broadcast(socket, data)
        
    def broadcast(self, socket, data):
        for player_socket in self.socket_list:
            if player_socket != self.sock and player_socket != socket:
                name = chat_engine.users[player_socket]
                chat_engine.users[name].send(data)
        
        self.recieved.put(data)
        
    def broadcasting(self, socket):
        def sending(data):
            try:
                socket.send(data)
            except:
                self.socket_disconnected(socket)
                
        if socket != self.sock:
            if socket in self.socket_list:
                if socket in self.waiting_chattername.keys():
                    self.waiting_chattername[socket].get(sending)
                elif socket in chat_engine.socket_names.keys():
                    name = chat_engine.socket_names[socket]
                    chat_engine.users[name].get(sending)
                        
    def socket_disconnected(self, socket):
        if socket in self.socket_list:
            self.socket_list.remove(socket)
            if socket in chat_engine.socket_names.keys():
                name = chat_engine.socket_names[socket]
                del chat_engine.socket_names[socket]
                self.broadcast(socket, '#Disconnected ' + name)
        
    def send(self, data):
        for player_socket in self.socket_list:
            if player_socket in chat_engine.socket_names.keys():
                name = chat_engine.socket_names[player_socket]
                chat_engine.users[name].send(data)

    def get(self, function):
        if not self.recieved.empty():
            function(self.recieved.get())
            self.recieved.task_done()

    def stop(self):
        self.running = False
    
# ----- ----- ----- ----- ----- --*-- ----- ----- ----- ----- ----- #
#                               Client                              #
# ----- ----- ----- ----- ----- --*-- ----- ----- ----- ----- ----- #
class Client(tcp_network.Client):
    def __init__(self, host, port=9012):
        tcp_network.Client.__init__(self, host, port)
        self.recieved = Queue.Queue()
        self.outgoing = Queue.Queue()

    def sending(self, socket):
        if not self.outgoing.empty():
            socket.send(self.outgoing.get())
            self.outgoing.task_done()      

    def recieving(self, data):
        if data.startswith('@@'):
            d = data.split()
            if data.startswith('@@Accept'):
                self.send('@@Name ' + chat_engine.name)
        else:
            self.recieved.put(data)

    def send(self, data):
        self.outgoing.put(data)

    def get(self, function):
        if not self.recieved.empty():
            function(self.recieved.get())
            self.recieved.task_done()

    def stop(self):
        self.running = False    

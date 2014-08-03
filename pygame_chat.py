import pygame
import network
import ui_tools.screen as screen
import ui_tools.textbox as textbox

pygame.init()

def get_connection(data):
    if len(data) > 2:
        host = data[2]
    else:
        host = '0.0.0.0'
        
    if len(data) > 3:
        port = int(data[3])
    else:
        port = 9009
        
    return host, port

class Chat(screen.Scene):
    def __init__(self):
        screen.Scene.__init__(self)
        self.wordlist = []
        self.renderlist = []
        self.connection = None
        self.text_color = (255,255,255)
        
        self.internal_font = pygame.font.Font(None, 24)
        height = self.internal_font.size('Ay')[1]
        self.spacer = int(height / 2.5) + height
        self.max_length = int(540 / self.spacer)
        self.scroll = 0
        
        self.name = 'Host'
        self.ID = '1'        
        
        style = textbox.default_image((600,40))
        self.text = textbox.Textbox(self, (0, 552), pygame.font.Font(None, 32), image=style, return_call=self.text_send)
        self.bind_event(pygame.QUIT, self.on_quit)
        
    def on_host(self, data):
        d = data.split()
        self.name = d[1]
        host, port = get_connection(d)

        self.connection = network.HostServer(host, port, self.name)
        self.connection.start()
        if self.connection.running:
            self.wordlist.append('Welcome to your chatroom')
            self.render()
        
    def on_client(self, data):
        d = data.split()
        self.name = d[1]
        host, port = get_connection(d)
        self.connection = network.Client(host, port, self.name)
        self.connection.start()
        if self.connection.running:
            self.wordlist.append('Welcome to the chatroom')
            self.render()
        
    def on_quit(self, event):
        if self.connection:
            self.connection.stop()
            self.connection.join()
        screen.handler.running = False
        
    def blit(self, surface):
        surface.fill((0,0,0))
        for image, position in self.renderlist:
            surface.blit(image, position)
        
    def update(self, tick):
        if self.connection:
            data = self.connection.get()
            if data:
                self.wordlist.append(data)
                self.render()
        
    def render(self):
        self.renderlist = []
        length = len(self.wordlist)
        if length > self.max_length:
            start = length - self.max_length - self.scroll
            end = length - self.scroll
            datalist = self.wordlist[start:end]
        else:
            datalist = self.wordlist
        datalist = datalist[::-1]
        
        step = self.max_length
        for word in datalist:
            image = self.internal_font.render(word, 1, self.text_color)
            position = (10, step * self.spacer)
            self.renderlist.append((image, position))
            step -= 1
        
    def text_send(self, text):
        if self.connection is None:
            if text.startswith('/host'):
                if len(text.split()) > 1:
                    self.on_host(text)
            elif text.startswith('/client'):
                if len(text.split()) > 1:
                    self.on_client(text)
        else:
            data = '{0} : {1}'.format(self.name, text)
            self.wordlist.append(data)
            self.connection.send(data)
            self.render()

if __name__ == '__main__':
    handle = screen.Handler('Pygame Chat', (800, 600))
    screen.handler.scenes['chat'] = Chat()
    handle.loop('chat', 20)
    pygame.quit()

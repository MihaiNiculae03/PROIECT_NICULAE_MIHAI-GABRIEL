import socket
import threading
from typing import Dict, List

HOST = "127.0.0.1"
PORT = 3334

class TopicServer:
    def __init__(self): #intializeaza serverul cu liste goale de clienti si topicuri 
        self.clients = []
        self.topics = {}
        self.lock = threading.Lock()

    def add_client(self, client, address):
    #adauga un client nou la lista de clienti
        with self.lock:
            self.clients.append((client, address))

    def remove_client(self, client):
    #sterge un client din lista de clienti si din toate topicurile la care este abonat
        with self.lock:
            self.clients = [c for c in self.clients if c[0] != client]
            for topic in self.topics.values():
                if client in topic:
                    topic.remove(client)

    def subscribe(self, topic, client, address):
        #adauga un client la lista de clienti abonati la un topic
        with self.lock:
            if topic not in self.topics:
                self.topics[topic] = []
            self.topics[topic].append(client)
            self.propagate_command(f"subscribe {topic} {address}", client)

    def unsubscribe(self, topic, client, address):
        #sterge un client din lista de clienti abonati la un topic
        with self.lock:
            if topic in self.topics and client in self.topics[topic]:
                self.topics[topic].remove(client)
                self.propagate_command(f"unsubscribe {topic} {address}", client)

    def publish(self, topic, message):
        #trimite un mesaj la toti clientii abonati la un topic
        with self.lock:
            if topic in self.topics:
                for client in self.topics[topic]:
                    self.send_message(client, message)

    def send_message(self, client, message):
        #trimite un mesaj catre un client
        try:
            if isinstance(message, bytes):
                client.sendall(message)
            else:
                client.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending message to {client}: {e}")

    def propagate_command(self, command, source_client): # trimite un mesaj catre toti clientii conectati la server, cu exceptia clientului sursa
        for client, address in self.clients:
            if client != source_client:
                self.send_message(client, command)

global_state = TopicServer()

def handle_client(client_socket, address):
    global_state.add_client(client_socket, address)
    
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            try:
                parts = data.decode('utf-8').split(' ')
                command = parts[0]
                
                if command == "subscribe" and len(parts) > 1:
                    topic = parts[1]
                    global_state.subscribe(topic, client_socket, address)
                elif command == "unsubscribe" and len(parts) > 1:
                    topic = parts[1]
                    global_state.unsubscribe(topic, client_socket, address)
                elif command == "publish" and len(parts) > 2:
                    topic = parts[1]
                    message = ' '.join(parts[2:])
                    global_state.publish(topic, message)
                elif command == "contact" and len(parts) > 1:
                    client_port = parts[1]
                    print(f"Client {address[0]}:{address[1]} can be contacted at port {client_port}")
                    global_state.propagate_command(f"New client on server, can be contacted at: {address[0]} port: {client_port}", client_socket)
                elif command == "connect_client" and len(parts) > 2:
                    client_ip, client_port = parts[1], int(parts[2])
                    print(f"Client {address[0]}:{address[1]} is connecting to {client_ip}:{client_port}")
                    global_state.propagate_command(f"connect_client {client_ip} {client_port}", client_socket)
                elif command == "disconnect":
                    print(f"Client {address[0]}:{address[1]} has disconnected")
                    global_state.propagate_command(f"disconnect {address[0]}:{address[1]}", client_socket)
                    global_state.remove_client(client_socket)
                    break
                else:
                    print(f"Invalid command or insufficient parameters: {data.decode('utf-8')}")
            except UnicodeDecodeError:
                print(f"Received binary data: {data}")
                parts = data.split(b' ', 2)
                if len(parts) > 2:
                    topic = parts[1].decode('utf-8')
                    message = parts[2]
                    global_state.publish(topic, message)
    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        global_state.remove_client(client_socket)
        client_socket.close()
        print(f"{address[0]}:{address[1]} has disconnected")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server listening on {HOST}:{PORT}")

        try:
            while True:
                client_socket, client_address = server.accept()
                print(f"\nAccepted connection from {client_address[0]}:{client_address[1]}")
                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
                client_thread.start()
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            server.close()

if __name__ == '__main__':
    main()

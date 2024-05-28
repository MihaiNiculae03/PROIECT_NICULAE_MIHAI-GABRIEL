import socket
import threading
import sys
import time

SERVERS = [('127.0.0.1', 3333), ('127.0.0.1', 3334)]  
CLIENTS = []  
PORT = 0  

def listen_for_messages(sock): #primeste mesajele si le afiseaza
    try:
        while True:
            message = sock.recv(1024)
            if not message:
                print("\nConnection closed by server.")
                break
            if message.decode('utf-8').startswith("New client on address") or message.decode('utf-8').startswith("disconnect"):
                print(f"\nMessage from server: {message.decode('utf-8')}")
            elif message.decode('utf-8').startswith("connect_client"):
                parts = message.decode('utf-8').split(' ')
                print(f"\nClient {parts[1]} connected to client {parts[2]}")
            else:
                try:
                    print(f"\nMessage from server: {message.decode('utf-8')}")
                except UnicodeDecodeError:
                    print(f"\nReceived binary data: {message}")
            print("> ", end='', flush=True)
    except Exception as e:
        print("Error receiving message:", e)

def send_command(sock, command): #trimite comanda catre server
    try:
        sock.sendall(command.encode('utf-8'))
    except Exception as e:
        print("Error sending command:", e)

def send_binary_message(sock, message, topic): # trimite mesaj binar catre server pentru un anumit topic
    try:
        message = b'publish ' + topic.encode('utf-8') + b' ' + message
        sock.sendall(message)
    except Exception as e:
        print("Error sending binary message:", e)

def convert_binary_string_to_bytes(binary_string): # converteste un string binar intr-un sir de bytes
    byte_length = (len(binary_string) + 7) // 8
    return int(binary_string, 2).to_bytes(byte_length, byteorder='big')

def connect_to_server(): # conecteaza clientul la un server din lista de servere
    for server in SERVERS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(server)
            print(f"Connected to server {server[0]}:{server[1]} from local address {sock.getsockname()[0]}:{sock.getsockname()[1]}")
            return sock
        except Exception as e:
            print(f"Failed to connect to server {server}: {e}")
    print("Unable to connect to any server.")
    sys.exit(1)

def connect_to_client(client_address): # conecteaza clientul la un alt client
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(client_address)
        print(f"Connected to client {client_address[0]}:{client_address[1]} from local address {sock.getsockname()[0]}:{sock.getsockname()[1]}")
        return sock
    except Exception as e:
        print(f"Failed to connect to client {client_address}: {e}")
    return None

def start_client_server(): # porneste clientul ca server pentru a accepta conexiuni
    global PORT
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('0.0.0.0', 0))
    server_sock.listen(5)
    PORT = server_sock.getsockname()[1]
    print(f"Client server listening on port {PORT}")

    def handle_connection(client_sock):
        try:
            while True:
                data = client_sock.recv(1024)
                if not data:
                    break
                try:
                    print(f"\nMessage received by client server: {data.decode('utf-8')}")
                    parts = data.decode('utf-8').split(' ', 2)
                    command = parts[0]
                    params = parts[1:]
                    if command == "subscribe":
                        if params:
                            topic = params[0]
                            print(f"Subscribed to {topic}")
                    elif command == "unsubscribe":
                        if params:
                            topic = params[0]
                            print(f"Unsubscribed from {topic}")
                    elif command == "publish":
                        if len(params) > 1:
                            topic, message = params[0], ' '.join(params[1:])
                            print(f"Received message for {topic}: {message}")
                    elif command == "disconnect":
                        print("Client disconnected.")
                    elif command == "connect_client":
                        if len(params) == 2:
                            client_ip, client_port = params[0], int(params[1])
                            CLIENTS.append((client_ip, client_port))
                            print(f"New client connected: {client_ip}:{client_port}")
                except UnicodeDecodeError:
                    print(f"\nReceived binary data: {data}")
        except Exception as e:
            print(f"Error handling client connection: {e}")
        finally:
            client_sock.close()

    def accept_connections():
        while True:
            client_sock, client_addr = server_sock.accept()
            print(f"Accepted connection from {client_addr}")
            threading.Thread(target=handle_connection, args=(client_sock,)).start()

    threading.Thread(target=accept_connections).start()

def show_menu():
    print("\nCommand Menu:")
    print("1. Subscribe to a topic")
    print("2. Unsubscribe from a topic")
    print("3. Publish a message to a topic")
    print("4. Connect to another client")
    print("5. Send a binary message")
    print("6. Exit")

def main():
    start_client_server()
    sock = connect_to_server()

    send_command(sock, f"contact {PORT}")

    print("Connected to server. Enter commands. Type 'exit' to quit.")
       
    listen_thread = threading.Thread(target=listen_for_messages, args=(sock,))
    listen_thread.start()

    while True:
        time.sleep(2)  
        show_menu()  
        choice = input("Select an option: ").strip()
        if choice == '6' or choice.lower() == 'exit':
            print("Sending disconnect command to server.")
            send_command(sock, "disconnect")
            break
        elif choice == '1':
            topic = input("Enter the topic to subscribe: ").strip()
            if topic:
                send_command(sock, f"subscribe {topic}")
                print(f"Subscribed to topic: {topic}")
            else:
                print("Topic cannot be empty.")
        elif choice == '2':
            topic = input("Enter the topic to unsubscribe: ").strip()
            if topic:
                send_command(sock, f"unsubscribe {topic}")
                print(f"Unsubscribed from topic: {topic}")
            else:
                print("Topic cannot be empty.")
        elif choice == '3':
            topic = input("Enter the topic to publish to: ").strip()
            message = input("Enter the message to publish: ").strip()
            if topic and message:
                send_command(sock, f"publish {topic} {message}")
                print(f"Published message to topic {topic}: {message}")
            else:
                print("Topic and message cannot be empty.")
        elif choice == '4':
            client_ip = input("Enter the client IP to connect to: ").strip()
            client_port = input("Enter the client port to connect to: ").strip()
            if client_ip and client_port.isdigit():
                client_port = int(client_port)
                new_client_sock = connect_to_client((client_ip, client_port))
                if new_client_sock:
                    send_command(sock, "disconnect")
                    send_command(new_client_sock, f"connect_client {sock.getsockname()[0]} {sock.getsockname()[1]}")
                    sock = new_client_sock
            else:
                print("Invalid IP or port.")
        elif choice == '5':
            topic = input("Enter the topic to publish to: ").strip()
            binary_data = input("Enter the binary data to send (e.g., '101010'): ").strip()
            if topic and binary_data:
                try:
                    message = convert_binary_string_to_bytes(binary_data)
                    send_binary_message(sock, message, topic)
                    print(f"Sent binary message to topic {topic}: {message}")
                except ValueError:
                    print("Invalid binary data format.")
            else:
                print("Topic and binary data cannot be empty.")
        else:
            print("Unknown command. Please try again.")

    listen_thread.join()

if __name__ == '__main__':
    main()

#! /usr/bin/env python2
#
# file: peer.py
#
# author: Tim van Deurzen
#
# A class that implements a simple chat peer.
#

import socket
import select
import logging
import sys

class ChatPeer:
    """
    Simple chat client that uses a name-server to lookup the address for a
    certain nickname and makes a peer-to-peer connection with that user for the
    actual chat conversation.
    """

    BUFFER_SIZE = 1024

    def __init__( self
                , name_server_ip = '127.0.0.1'
                , name_server_port = 3456
                , client_listen_port = 1234
                , listen_queue_size = 5
                ):

        """
        Initialize the ChatPeer setting all the relevant variables to their
        given or default values.
        """

        self.nickname = None

        self.name_server_ip = name_server_ip
        self.name_server_port = name_server_port
        self.name_server_sock = None
        self.connected = False

        self.client_listen_port = client_listen_port
        self.listen_queue_size = listen_queue_size
        self.client_listen_sock = None

        # Peers not yet handshaken
        self.incomming_peers = {}
        # Mapping from peer nicknames to their connection information.
        self.peers = {}

        # Mapping from sockets to nicknames.
        self.socks2names = {}
    
        self.socks2names[sys.stdin] = "stdin"

        # Create a log object.
        # logging.basicConfig( filename="ChatPeer.log"
        #                   , level=logging.DEBUG
        #                  , format = '[%(asctime)s] %(levelname)s: %(message)s'
        #                   , filemode='a'
        #                   )
        logging.basicConfig( level=logging.DEBUG
                           , format = '[%(asctime)s] %(levelname)s: %(message)s'
                           )
        self.logger = logging.getLogger('ChatPeer')

        # You should setup the necessary sockets and data structures here. 
        #
        # A peer needs to be able to accept connections from other peers and
        # needs to be connected with the name server. The peer needs to
        # multiplex between all these sockets and respond according to the
        # protocol whenever a message is received.
        #
        # HINT: Have a look at all the imported modules to see which functions
        # they provide.
        #
        # HINT: stdin (for keyboard interaction) can be approached as a socket.
        #
        self.setup_client_listener()


    def setup_name_server(self):
        """
        Try to connect with the name server.
        """

        # Setup the connection with the name server.
        try:
            self.name_server_sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)

            self.name_server_sock.connect((
                self.name_server_ip,
                self.name_server_port))

            self.connected = 1
        except:
            self.logger.exception("Failed connecting with name server")
            self.connected = 0
            return 1

        # Use the logger object whenever a significant event occurs (such as
        # successfully or unsuccessfully connecting with the name server).
        #
        self.logger.info("Connected to name server: %s" % self.name_server_ip)
        return 0

    def setup_client_listener(self):
        """
        Try to setup the peer to accept connections from other peers.
        """

        # Set the peer up to accept connections from other peers.
        self.client_listen_sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        self.client_listen_sock.setsockopt(
            socket.SOL_SOCKET, 
            socket.SO_REUSEADDR,
            1
        );

        self.client_listen_sock.bind(('', self.client_listen_port))
        self.client_listen_sock.listen(self.listen_queue_size)

        pass


    def run(self):
        """
        The main ChatPeer loop.
        """

        running = 1
        
        while running:
            # Print a simple prompt.
            

            # In this loop you should:
            iss = []
            iss = self.socks2names.keys()
            iss.extend(self.incomming_peers.keys())
            if self.client_listen_sock: 
                iss.append(self.client_listen_sock)
            if self.name_server_sock:
                iss.append(self.name_server_sock)



            # outsocks used to check if it is ready to send to
            oss = self.socks2names.keys()
            
            
            
            rr, wr, er = select.select(iss, [], [])
            # some = sys.stdin.readline()
            

            for s in rr:
                if(s == sys.stdin):
                    # - Check if anything was entered on the keyboard.
                    
                    sys.stdout.write('\n> ')
                    sys.stdout.flush()
                    sys.stdout.flush()

                    data = sys.stdin.readline()
                    if data:
                       self.parse_msg(data)
                elif(s == self.client_listen_sock):
                    # - Check if a new peer is trying to connect with you.
                    #Accept and handshake
                    client, addr = s.accept()
                    self.incomming_peers[client] = addr
                else:
                    # - Check if the name server is trying to send you a message
                    # - Check if a peer is trying to send you a message.
                    msg = s.recv(ChatPeer.BUFFER_SIZE)
                    if msg:
                        self.parse_and_print(msg, s)
                    else:
                        # Do something error ish
                        debug = 3
            #running = 0


    def parse_and_print(self, msg, sock):
        """
        Interpret any commands sent by peers or the name server and
        (potentially) display a message to the user.
        """

        parts = msg.split()

        if(sock == self.name_server_sock):
            print "FROM NS: %s" % msg
            if parts[0] == "100":
                # Great success
                print("Server answered 100")
                debug = 2
                
            elif parts[0] == "101":
                # Nick taken
                print "Please chose a different nickname"
                self.name_server_sock.close()
                self.name_server_sock = None
                self.connected = False
                self.nickname = None
                return 1

            elif parts[0] == "102":
                # Jackass server
                debug = 4
                self.nickname = None

            else:
                # FATAL - returned something completely wrong
                debug = -1
                self.nickname = None

        elif len(parts) > 2 and sock in self.incomming_peers:
            #Socket is non handshaken incomming peer
            # socket, address information, part[1,2]=nick,port, False - callee
            if parts[0] != "HELLO":
                sock.send("202 REGISTRATION REQUIRED")
                return

            self.logger.info("REQUEST Received from incomming peer: %s" % msg)
            self.handshake_peer(sock, self.incomming_peers[sock],
                parts[1], parts[2], False)
        else:
            if(len(parts) > 2 and parts[0] == "MSG"):
                peer_nick = parts[1]
                message = ' '.join(parts[2:])
                print "%s says: %s" % (peer_nick, message)

            elif(len(parts) > 1 and parts[0] == "LEAVE"):
                try:
                    peer_nick = parts[1]
                    del self.socks2names[sock]
                    del self.peers[peer_nick]
                    sock.send("600 BYE")
                    sock.disconnect()
                    sock.close()
                except:
                    print "Somebody tried leaving"
                    sock.send("601 ERROR")
            else:
                print "You might have received unwanted messages"
                print "%s" % msg
        # You should analyse the message and respond according to the protocol.
        # You may assume that any message that does not adhere to the protocol
        # is garbage and can be discarded.


    def handshake_name_server(self, nickname):
        """
        Register the user with the server using a specific nickname.
        """

        if not self.connected:
            self.logger.warn('Attempted handshake without being connected.')

            print "Not connected to the server."

            return
        
        # Perform the handshake protocol.
        handshake_msg = "HELLO %s %s" % (nickname, str(self.client_listen_port))
        res = self.name_server_sock.send(handshake_msg)

        print("Setting self.nickname=%s" % nickname)
        self.nickname = nickname

       
    def handshake_peer( self
                      , sock
                      , addr
                      , nick = None
                      , port = None
                      , caller = False
                      ):

        """
        Perform a handshake protocol with another peer, either as the caller or
        the callee.
        """

        if caller:
            # This peer is initiating the connection and should start the
            # handshake protocol.
            sock.send("HELLO %s %s" %(self.nickname, self.client_listen_port))
            data = sock.recv(ChatPeer.BUFFER_SIZE)
            parts = data.split()

            # Callee has refused to engage a chat session
            if parts[0] == "201":
                print "Peer refused connection"
            # You need to register
            elif parts[0] == "202":
                print "Registration required"
            # Handshake incomplete
            elif parts[0] == "203":
                print "Not enough information to handshake"
            elif parts[0] == "200":
                print "Connected"
                self.socks2names[sock] = nick
                self.peers[nick] = (sock, addr, port)
            # Teh hurr
            else:
                print "derp peer"

        else:
            # We are responding to a handshake from another peer.
            if nick == "None" and nick in self.peers.keys():
                sock.send("201 REFUSED")
                self.logger.info("Refused other peer - nick None or taken")

            else:
                try:
                    _, port = addr
                    self.socks2names[sock] = nick
                    self.peers[nick] = (sock, addr, port)
                    sock.send("200 CONNECTED")
                    self.logger.info("Sucess - peer connected")
                except:
                    sock.send("201 REFUSED")
                    self.logger.warning("Peer refused - faulty request")

            del self.incomming_peers[sock]

    
    def parse_msg(self, msg):
        """
        Parse the user's input and perform the associated action.
        """

        parts = msg.split()

        if len(parts) == 0:
            print("Type /help if you need some")
        elif parts[0] == "/connect" and len(parts) >= 3: 
            #format /connect ip port [nick]
            if self.connected:
                self.logger.info('Closing name-server connection and opening ' \
                                 'new connection.')

                print 'Disconnecting from name-server and connecting to new ' \
                      'name-server.'
                
                # Close the connection with the name server.

            # Get the hostname and port number from the commandline entered by
            # the user.
            self.name_server_ip = socket.gethostbyname(parts[1])
            self.name_server_port = int(parts[2])

            if self.setup_name_server() is 0:
                self.connected = True

                if self.nickname is None and len(parts) == 4:
                    self.handshake_name_server(parts[3])

                elif self.nickname is None:
                    print "Please choose a nickname and use '/register' to " \
                          "register."

                else:
                    self.handshake_name_server(self.nickname)
            else:
                print "Couldn't establish connection to '%s'." % parts[1]

        elif parts[0] == "/nick" and len(parts) > 1:
            # format /nick <nickname>
            self.nickname = parts[1]

        elif parts[0] == "/register":
            if self.nickname == None:
                print "No nickname chosen"
            else:
                self.handshake_name_server(self.nickname)

        elif parts[0] == "/msg" and len(parts) > 2:
            # format: /msg <nick> <message>
            print("Sending message to: %s, isSelf: %s" % (parts[1], parts[1] == self.nickname))
            if parts[1] == self.nickname:
                print "Cannot send a private message to yourself."
                return 
            
            if parts[1] == '*':
                self.broadcast(' '.join(parts[2:]))
                return
            elif not self.connected:
                self.logger.error('Could not connect to peer because we are ' \
                                  'not connected to the name-server.')

                print "Could not connect to peer '%s'" % parts[1]
                return
            elif parts[1] not in self.peers and self.connected:
                addr, port = self.get_nick_addr(parts[1])
                p_sock = self.connect_to_peer(addr, port)
                print "Addr: %s Port: %s" % (addr, str(port))
                # parts[1] is the nick, and we set True to let the method know
                # that we are the caller
                if(p_sock == 1):
                    p_sock = self.connect_to_peer(addr,port)

                if(p_sock == 1):
                    return
                self.handshake_peer(p_sock, addr, parts[1], port, True)

                # Connect with the peer and peform the handshake protocol.
            
                        
            # Send the message to the peer.
            self.send_private_msg(parts[1], ' '.join(parts[2:]))

        elif parts[0] == "/all" and len(parts) > 1:
            # format: /all <msg>
            self.broadcast(' '.join(parts[1:]))
        
        elif parts[0] == "/leave":
            # format: /leave
            self.disconnect()

        elif parts[0] == "/help":
            print 'Step 1: /connect <hostname> <port>'
            print 'Step 2: /nick <nickname>'
            print 'Step 3: /register'
        elif parts[0] == "/quit":
            # format: /quit
            print 'Shutting down...'

            self.disconnect()
            sys.exit(0)

        else:
            # Either we assume that normal messages (i.e. not commands) are
            # always sent to the last person that received a private mssage or
            # we make normal messages broadcasts.
            
            if self.connected:
                pass
            else:
                print "Not connected!"


    def broadcast(self, msg):
        """
        Broadcast a message to all connected users.
        """

        # Acquire a list of users from the name server and send the message to
        # all users.

        self.name_server_sock.send("USERLIST")
        data = self.name_server_sock.recv(ChatPeer.BUFFER_SIZE)
        while (data == None):
               data = self.name_server_sock.recv(ChatPeer.BUFFER_SIZE)

        print data
        parts = data.split()
        if parts[0] == "300":
               # If 300, then we get a userlist back, and we need to send to them
               numpeers = int(parts[2])
               i = 0
               peerinfo = parts[3:]
               while i < numpeers:
                    try:
                        username = peerinfo[i * 3]
                        addr = peerinfo[(i * 3) + 1]
                        port = peerinfo[(i * 3) + 2]
                        if port.endswith(','): port = port[:len(port)-1]
                        port = int(port)
                        p_sock = 1
                        existing = False
                        try:
                            p_sock,_,_ = self.peers[username]
                            existing = True
                        except:
                            p_sock = self.connect_to_peer(addr, port)
                            self.handshake_peer(p_sock, addr, username, port, True)
                        # Send the message to the peer.
                        print p_sock
                        if p_sock != 1:
                            print "sending msg to %s" %username
                            self.send_private_msg(username, msg)
                            if not existing:
                                del self.socks2names[p_sock]
                                del self.peers[username]
                                p_sock.close()
                    except:
                        self.logger.exception("something went wrong...ups")
                    i += 1
        elif parts[0] == "301":
               # In this case we are the only user, no action taken
               print "forever alone"


    def disconnect(self):
        """
        Disconnect from the name server and all peers.
        """
        
        # For all of the sockets currently active, except STDIN and our listening
        # socket perform the LEAVE protocol.
        if len(self.incomming_peers) > 0:
            # Remove these incomming peers
            # Aka just shut them down
            for s in self.incomming_peers:
                s.close()

        if len(self.socks2names.keys()) > 1:
            # Perform leave
            # and close tha socks
            for s in self.socks2names.keys():
                if not s == sys.stdin:
                    s.close()
                    del self.socks2names[s]

        self.peers = {}
        self.socks2names = {}
        self.connected = False


    def connect_to_peer(self, addr, port):
        """
        Establish a peer-to-peer connection with another peer.
        """

        print "Connecting to %s:%s" % (addr, str(port))

        try:
            peer_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)

            peer_socket.connect((
                addr,
                port))
            return peer_socket

        except:
            self.logger.exception("Failed connecting with peer")
            print "FAIL When connection to peer"
            return 1

        
        # This function should return the newly created socket.
        

    def send_private_msg(self, nick, msg):
        """
        Send a private message to a peer.
        """

        sock, _, _ = self.peers[nick]

        sock.send('MSG %s %s' % (self.nickname, msg))

    
    def get_nick_addr(self, nick):
        """
        Get the address belonging to a specific nick name.
        """
        self.name_server_sock.send("LOOKUP %s" % nick)

        data = self.name_server_sock.recv(ChatPeer.BUFFER_SIZE)
        parts = data.split()

        if len(parts) > 1 and parts[0] == "404":
            dummy = "dummy"
        elif len(parts) > 3 and parts[0] == "400":
            try:
                port = int(parts[3])
                return (parts[2], port)
            except:
                self.logger.error("Shit happened")
                        

        # This function should return the ip address and a port number that
        # user 'nick' can be reached at.

            

###
### Main method, run the peer with default values or a custom listening port.
###

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Interpret the first command-line argument as the port number this
        # peer will listen on.
        ChatPeer(client_listen_port = int(sys.argv[1])).run()
    else:
        ChatPeer().run()

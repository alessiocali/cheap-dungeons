import random
import socket as sck
import math

#####################################################################################################################
#       IMPORTANT NOTE                                                                                              #
#####################################################################################################################
#   Throughout the file x and y symbols are used to refer to elements within the grid. These ARE NOT intended to be #
#   x = abscissa / y = ordinate. Rather x = row, y = column. It's counter-intuitive, but it is due to how the grid  #
#   is accessed (if I print data[i][j] in a double i,j loop it will first access each row and then its subsequent   #
#   elements).                                                                                                      #
#####################################################################################################################

MULTI_PORT = 8390
DUNGEON_SIZE = 25  # Dungeon grid size per side
DUNGEON_SIGHT = 6  # Player is shown nearby [x - sight, x + sight] x [y - sight, y + sight] cells
STUP_DST = 10  # The minimum distance between players and exit during setup
STUP_TOL = 10  # The number of possible setup failures before decreasing the minimum distance.
CORRIDOR_BIAS = 0.4  # The probability by which the drunken path will go straight
CORRIDOR_CM_BIAS = (1 - CORRIDOR_BIAS) / 3  # Complementary corridor bias. The probability of all other sides.
DRUNK_LIMIT = 200  # The max number of cell explorable during drunken walk
DRUNK_CHANCE = 0.3  # The probability that when connecting a cell and the exit, a drunken walk will be performed

PC_MNST = 0.05  # Percentage of monsters over the free cells
PC_TRAP = 0.05  # Percentage of traps
PC_QUIZ = 0.025  # Percentage of traps
PC_CHEST = 0.05  # Percentage of chests

RM_WALL = '#'  # All the map symbols
RM_EMPTY = ' '
RM_PLAYER = '@'
RM_PLAYER2 = '$'
RM_EXIT = 'E'
RM_MNST = 'm'
RM_TRAP = 't'
RM_QUIZ = 'q'
RM_CHEST = 'c'
RM_UNKNW = '?'

RM_KNIFE = 'k'
RM_LOCKP = 'l'
RM_COMP = 'C'
RM_SWRD = 's'

MSG_DIE = "DEAD"
MSG_ESC = "ESCAPE"
MSG_CLR = "CLEAR"
MSG_POS = "POS"

DIRECTIONS = ("Nord-Ovest", "Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ovest")

cheats_enabled = False


# Dungeon data
class DungeonGraph:
    data = []  # The actual grid
    p1 = None  # Player 1 position
    exit = None  # Exit position
    p2 = None  # Player 2 position
    ui_counter = 0  # Counter used to draw UI lines

    def __init__(self, multi):
        # Generate empty
        for i in range(0, DUNGEON_SIZE):
            self.data += [[]]
            for j in range(0, DUNGEON_SIZE):
                self.data[i] += [RM_WALL]

        random.seed()

        # Spawn random P1
        self.p1 = random_coord()
        self.set(self.p1, RM_EMPTY)  # Player cell is freed. Player symbol is drawn with print functions

        min_dst = STUP_DST
        try_count = 0

        # Spawn random exit distant at least min_dst
        while True:
            self.exit = random_coord()
            if tpl_dst(self.p1, self.exit) > min_dst:
                self.set(self.exit, RM_EXIT)
                break
            else:
                try_count += 1
                if try_count > STUP_TOL:    # Decrease min_dst after STUP_TOL failures
                    min_dst = max([min_dst - 1, 1])
                    try_count = 0

        min_dst = STUP_DST
        try_count = 0

        # On multiplayer mode, spawn random P2
        if multi:
            while True:
                self.p2 = random_coord()
                if tpl_dst(self.p1, self.p2) > min_dst and tpl_dst(self.exit, self.p2) > min_dst:
                    self.set(self.p2, RM_EMPTY)
                    break
                else:
                    try_count += 1
                    if try_count > STUP_TOL:
                        min_dst = max([min_dst - 1, 1])
                        try_count = 0

        # Connect P1 and exit through drunken star method
        self.drunken_star(self.p1, self.exit)

        if multi:  # Do the same to connect P1-P2 and exit-P2 on multiplayer
            self.drunken_star(self.p1, self.p2)
            self.drunken_star(self.exit, self.p2)

        empties = self.get_empty()
        empties_len = len(empties)

        # Get the total count of all map elements
        mnst_count = int(empties_len * PC_MNST)
        trap_count = int(empties_len * PC_TRAP)
        quiz_count = int(empties_len * PC_QUIZ)
        chest_count = int(empties_len * PC_CHEST)

        knives_count = random.randint(1, 2)
        swords_count = random.randint(1, 2)

        symbols = (RM_MNST, RM_TRAP, RM_QUIZ, RM_CHEST, RM_KNIFE, RM_SWRD, RM_COMP, RM_LOCKP)
        counts = (mnst_count, trap_count, quiz_count, chest_count, knives_count, swords_count, 1, 2)

        # For each couple of symbols and amounts, fill random empty cells
        for s, c in [(symbols[i], counts[i]) for i in range(0, 8)]:
            self.place(s, c, empties)

    # Places a certain room_type within the given pos tuple
    def set(self, pos, room_type):
        self.data[pos[0]][pos[1]] = room_type

    # Retrieves the room at the given pos tuple, or None if out of bounds
    def get(self, pos):
        x, y = pos
        if 0 <= x < DUNGEON_SIZE and 0 <= y < DUNGEON_SIZE:
            return self.data[pos[0]][pos[1]]
        else:
            return None

    # Returns the array of north, south, east and west tuple, given they're within bounds
    def get_nearby(self, pos):
        nearby = []
        x, y = pos
        if x > 0:
            nearby += [(x - 1, y)]
        if x < DUNGEON_SIZE - 1:
            nearby += [(x + 1, y)]
        if y > 0:
            nearby += [(x, y - 1)]
        if y < DUNGEON_SIZE - 1:
            nearby += [(x, y + 1)]
        return nearby

    # Print the whole map
    def print(self):
        print(" " + "--- " * DUNGEON_SIZE)  # Top rule
        for i in range(0, DUNGEON_SIZE):
            for j in range(0, DUNGEON_SIZE):
                # If the (i, j) couple matches P1 or P2 print the Player symbol instead
                symbol = RM_PLAYER if (i, j) == self.p1 else RM_PLAYER2 if (i, j) == self.p2 else self.get((i, j))
                print("| " + symbol + " ", end="", flush=True)
            print("|")  # Termination bar
            print(" " + "--- " * DUNGEON_SIZE)  # Bottom rule

    # Print the UI, given current player position, radius of sight and player info
    def print_hidden(self, pos, radius, player_info):
        x, y = pos

        # Adjust "camera" center if near sides
        if x < radius:
            x = radius
        elif x > DUNGEON_SIZE - radius:
            x = DUNGEON_SIZE - radius

        if y < radius:
            y = radius
        elif y > DUNGEON_SIZE - radius:
            y = DUNGEON_SIZE - radius

        submatrix = []

        # Extract submatrix of nearby cells as (x, y) tuples
        for i in range(0, DUNGEON_SIZE):
            if x - radius <= i < x + radius:
                subrow = []
                # Extract elements of subrow i
                for j in range(0, DUNGEON_SIZE):
                    if y - radius <= j < y + radius:
                        # Hide elements unknown to the player; substitute player position symbol with RM_PLAYER
                        subrow.append(RM_PLAYER if (i, j) == self.p1
                                      else RM_PLAYER2 if (i, j) == self.p2 and (i, j) in player_info.discovered
                                      else self.data[i][j] if (i, j) in player_info.discovered
                                      else RM_UNKNW)

                submatrix.append(subrow)

        size = len(submatrix)

        # Print the submatrix. Similar to print() method
        print(" " + "--- " * size)
        for i in range(0, size):
            for j in range(0, size):
                print("| " + submatrix[i][j] + " ", end="", flush=True)
            print("|" + self.get_ui_line(player_info))
            print(" " + "--- " * size)

        self.ui_counter = 0

    # Get a new UI line at each call
    def get_ui_line(self, player_info):
        self.ui_counter += 1
        if self.ui_counter == 1:
            return "\t%s\t%d/%d PV\t %d Monete" % \
                (player_info.name, player_info.health, player_info.HP_MAX, player_info.coin)
        elif self.ui_counter == 2:
            return "\tOggetti"
        elif self.ui_counter == 3:
            lockpick = "Sì" if player_info.has_lockpick else "Nessuno"
            return "\tGrimaldello: %s" % lockpick
        elif self.ui_counter == 4:
            knife = "Sì" if player_info.has_knife else "Nessuno"
            return "\tColtello: %s" % knife
        elif self.ui_counter == 5:
            sword = "Sì" if player_info.has_sword else "Nessuna"
            return "\tSpada: %s" % sword
        elif self.ui_counter == 6:
            compass = "Sì" if player_info.has_compass else "Nessuna"
            return "\tBussola: %s" % compass
        else:
            return ""

    # Trace a Drunken Walk (choose a random direction) from start up to a limit number of cells
    def drunk_path(self, start, limit):
        drunk_count = 0
        pos = start
        dirs = [(0, 1), (-1, 0), (0, -1), (1, 0)]  # East, South, West, North. Remember it's (row, column)
        most_likely = (0, 1)
        seq = []

        while True:
            # Swap most likely direction to first index
            idx = dirs.index(most_likely)
            dirs[0], dirs[idx] = dirs[idx], dirs[0]
            rnd = random.random()

            # Pick a random direction, favoring the first one
            if rnd < CORRIDOR_BIAS:
                cur_dir = dirs[0]
            elif rnd < CORRIDOR_BIAS + CORRIDOR_CM_BIAS:
                cur_dir = dirs[1]
            elif rnd < CORRIDOR_BIAS + 2 * CORRIDOR_CM_BIAS:
                cur_dir = dirs[2]
            else:
                cur_dir = dirs[3]

            next_pos = pos[0] + cur_dir[0], pos[1] + cur_dir[1]

            # If chosen cell is valid (is within [0, 0]x[DUNGEON_SIZE - 1, DUNGEON_SIZE - 1])...
            if before((0, 0), next_pos) and before(next_pos, (DUNGEON_SIZE - 1, DUNGEON_SIZE - 1)):
                next_tile = self.get(next_pos)

                if next_tile == RM_EXIT:  # Stop if you reach the exit
                    break
                elif next_tile == RM_EMPTY or next_tile == RM_WALL:  # Else if wall or empty...
                    self.set(next_pos, RM_EMPTY)  # Free this tile
                    seq.append(next_pos)  # Add next position to sequence
                    pos = next_pos  # Update position
                    most_likely = cur_dir  # Update most likely direction
                    drunk_count += 1  # Step  counter
                    if drunk_count >= limit:
                        break  # Stop if reached the limit
                else:
                    continue
            else:
                continue  # Out of bounds, try again

        return seq

    # Connect start to goal through straight lines
    def connect_path(self, start, goal):
        current = start
        cx, cy = current
        gx, gy = goal

        # Move horizontally and then vertically until you reach the goal
        while True:
            if cx < gx:
                cx += 1
            elif cx > gx:
                cx -= 1
            elif cy < gy:
                cy += 1
            elif cy > gy:
                cy -= 1

            current = cx, cy
            if current == goal:
                break

            self.set(current, RM_EMPTY)     # Empty the current cell

            if random.random() < DRUNK_CHANCE:  # By DRUNK_CHANCE, do a Drunken Walk from the current cell
                self.drunk_path(current, DRUNK_LIMIT / 10)

    # Use drunken walk + connect_path to connect start and goal
    def drunken_star(self, start, goal):
        dr_path = self.drunk_path(start, DRUNK_LIMIT)   # Do a random walk from start
        connect_start = random.choice(dr_path)    # Connect goal to a random position in the path
        self.connect_path(connect_start, goal)

    # Get all empty cells as (x, y) tuples. Exclude player cells.
    def get_empty(self):
        return [(i, j) for i in range(DUNGEON_SIZE) for j in range(DUNGEON_SIZE) if
                self.data[i][j] == RM_EMPTY and (i, j) not in (self.p1, self.p2)]

    # Place count times symbol over the grid, given the list of empty cells
    def place(self, symbol, count, empties):
        placed = 0
        while placed < count:
            x, y = random.choice(empties)
            self.data[x][y] = symbol
            empties.remove((x, y))
            placed += 1


# Player data
class Player:
    name = "???"
    HP_MAX = 10
    COIN_MAX = 9999
    health = 10
    coin = 10
    discovered = set([])
    has_lockpick = False
    has_knife = False
    has_sword = False
    has_compass = False

    def attacked(self, health_lost):
        self.health = self.health - health_lost if self.health > health_lost else 0
        return self.health != 0

    def discover(self, new):
        self.discovered |= new


# Get a random coordinate except borders.
def random_coord():
    return random.randint(1, DUNGEON_SIZE - 2), random.randint(1, DUNGEON_SIZE - 2)


# Distance between coordinates is defined by taxicab-geometry rather then euclidean
def tpl_dst(a, b):
    x1, y1 = a
    x2, y2 = b
    return abs(x1 - x2) + abs(y1 - y2)


def before(ta, tb):
    return ta[0] < tb[0] and ta[1] < tb[1]


# Discover nearby rooms and print the hidden map
def update(curr_tile, player, dungeon):
    new_room = dungeon.get(curr_tile)

    # Add nearby rooms to discovered if Wall, Empty or Exit, plus current cell in any case
    newly_discovered = set([near_pos for near_pos in dungeon.get_nearby(curr_tile) if
                            dungeon.get(near_pos) in (RM_WALL, RM_EXIT, RM_EMPTY)] + [curr_tile])
    player.discover(newly_discovered)

    # Flag exit_found if the exit is nearby
    exit_nearby = dungeon.exit in newly_discovered

    # Print UI
    dungeon.print_hidden(curr_tile, DUNGEON_SIGHT, player)
    return new_room, curr_tile, exit_nearby


# Get input from player and decide the next cell. Cheats can be input here as well.
# Master code: JUSTINBAILEY
def move(curr_tile, socket, dungeon, player):
    x, y, nx, ny = None, None, None, None
    global cheats_enabled

    while True:
        print("Dove desideri andare?")

        pl_input = input()
        x, y = curr_tile
        nx, ny = x, y

        if pl_input == 'w':
            nx = x - 1
        elif pl_input == 'a':
            ny = y - 1
        elif pl_input == 's':
            nx = x + 1
        elif pl_input == 'd':
            ny = y + 1
        elif pl_input == '':
            print("Decidi di restare qui")
        elif pl_input == 'JUSTINBAILEY':
            cheats_enabled = not cheats_enabled
            print("Trucchi abilitati!" if cheats_enabled else "Trucchi disabilitati!")
        elif pl_input == "quit":
            if socket is not None:
                socket.close()
            exit()
        elif cheats_enabled:
            if pl_input == "triforce":      # Get the compass
                player.has_compass = True
                continue
            elif pl_input == "greyskull":   # Get the sword
                player.has_sword = True
                continue
            elif pl_input == "thievesguild":    # Get the lockpick
                player.has_lockpick = True
                continue
            elif pl_input == "cutthroat":   # Get the knife
                player.has_knife = True
                continue
            elif pl_input == "brighteyes":  # Cheat for printing the whole map
                dungeon.print()
                continue
            elif pl_input == "seppuku":  # Cheat for suicide
                player.attacked(player.health)
            elif pl_input == "escaperod":  # Cheat for exit
                dungeon.set(dungeon.p1, RM_EXIT)
        else:
            print("Input non riconosciuto.")
            continue

        next_room = dungeon.get((nx, ny))

        # Bump if wall or out of bounds
        if next_room == RM_WALL or next_room is None:
            print("Vi è un muro in quella direzione.")
            continue
        break

    return curr_tile, (nx, ny)


def play():
    print("  _______ _________   ___    ___  __  ___  _______________  _  ______")
    print(" / ___/ // / __/ _ | / _ \  / _ \/ / / / |/ / ___/ __/ __ \/ |/ / __/")
    print("/ /__/ _  / _// __ |/ ___/ / // / /_/ /    / (_ / _// /_/ /    /\ \  ")
    print("\___/_//_/___/_/ |_/_/    /____/\____/_/|_/\___/___/\____/_/|_/___/  ")
    print()
    print("Benvenuto a Cheap Dungeons!")
    print("Vuoi giocare in solo o con un amico? s/a")
    multi = input() == "a"

    dungeon = DungeonGraph(multi)
    player = Player()

    conn = None

    if multi:
        print("Desideri iniziare una nuova partita o connetterti ad una già esistente? n/c")
        type_mod = input()

        if type_mod == "c":
            conn = sck.socket(sck.AF_INET, sck.SOCK_STREAM)
            print("Immetti l'indirizzo ip del tuo avversario (assicurati che il tuo avversario sia in attesa)")
            ip_player = input()
            print("In attesa dell'avversario...")

            try:
                conn.connect((ip_player, MULTI_PORT))
            except ConnectionRefusedError:
                print("Indirizzo IP non valido oppure l'avversario non ha iniziato una partita")
                exit()

            msg = "DUNGEON"

            try:
                for i in range(DUNGEON_SIZE):   # Receive map row by row
                    conn.sendall(msg.encode())
                    dungeon.data[i] = list(conn.recv(1024).decode())
                    print("Ricezione mappa : " + str(float(i) / DUNGEON_SIZE * 100) + "%                ", end='\r')

                print("Riceziona mappa completata")

                # Receive P1 and P2
                pos_string = conn.recv(1024).decode()
                pos_p1 = pos_string.split(',')

                conn.sendall(msg.encode())
                pos_string = conn.recv(1024).decode()
                pos_p2 = pos_string.split(',')

                dungeon.p2 = int(pos_p1[0]), int(pos_p1[1])  # Positions are swapped because this is the second player
                dungeon.p1 = int(pos_p2[0]), int(pos_p2[1])

            except ConnectionAbortedError:
                print("Connessione interrotta dall'avversario")
                multi = False
                dungeon.p2 = None
                conn.close()

        else:
            print("In attesa dell'avversario...")
            c = sck.socket(sck.AF_INET, sck.SOCK_STREAM)  # Connection setup
            c.bind(("", MULTI_PORT))
            c.listen()
            conn, _ = c.accept()
            c.close()

            try:
                for i in range(DUNGEON_SIZE):   # Send map row by row
                    msg = conn.recv(1024).decode()
                    if msg == "DUNGEON":
                        conn.sendall(''.join(dungeon.data[i]).encode())
                        print("Invio mappa : " + str(float(i) / DUNGEON_SIZE * 100) + "%                  ", end='\r')

                print("Invio mappa completato")

                pos_string_p1 = str(dungeon.p1[0]) + ',' + str(dungeon.p1[1])
                pos_string_p2 = str(dungeon.p2[0]) + ',' + str(dungeon.p2[1])

                conn.sendall(pos_string_p1.encode())
                received = conn.recv(1024).decode()

                if received == "DUNGEON":
                    conn.sendall(pos_string_p2.encode())

            except ConnectionAbortedError:
                print("Connessione interrotta dall'avversario")
                multi = False
                dungeon.p2 = None
                conn.close()

    print("Senza ricordare il perché, ti ritrovi in un luogo a te non familiare...")
    print("Qual è il tuo nome?")

    player.name = input()

    # Some initialization
    msg_queue = []
    previous_tile = curr_tile = dungeon.p1
    escaped = False
    opponent_escaped = False
    opponent_dead = False
    wait_opponent = False
    movs_to_esc = 0
    opponent_gold = -1
    turnback = False

    with open("quiz.txt") as quiz_file:
        quizzes = [quiz.split('-') for quiz in quiz_file.readlines()]

    # GAME LOOP #
    while not escaped:
        room, curr_tile, exit_found = update(curr_tile, player, dungeon)
        msg_queue.clear()

        if opponent_escaped:
            print("In lontananza, senti la porta chiudersi. Ti rimangono 10 mosse, ne hai fatte: " + str(movs_to_esc))
        elif opponent_dead:
            print("Le urla strazianti di un altro avventuriero giungono alle tue orecchie.")
            opponent_dead = False

        if player.has_compass:
            direction = "Ovest"
            for i in range(7):
                max_ang = math.pi * (7 - 2*i) / 8
                min_ang = math.pi * (5 - 2*i) / 8
                ang = math.atan2(dungeon.p1[0] - dungeon.exit[0], dungeon.exit[1] - dungeon.p1[1])
                if min_ang < ang <= max_ang:
                    direction = DIRECTIONS[i]
                    break

            print("La bussola indica verso " + direction)

        # Player encounter cases
        if dungeon.p1 == dungeon.p2:
            turnback = True

            print("Di fronte a te si staglia uno sconosciuto...")
            print("Cosa desideri fare?")
            print("s - Saluta lo sconosciuto")
            if player.has_sword:
                print("a - Attacca lo sconosciuto")
            if player.has_knife:
                print("r - Deruba lo sconosciuto")
            choice = input()

            try:
                # Handle "Greet" cases
                if choice == "s":
                    print("Cosa vuoi dire allo sconosciuto?")
                    msg = input()

                    conn.sendall(("S:" + msg).encode())
                    opp_choice = conn.recv(1024).decode().split(":", 1)

                    if opp_choice[0] == "S":
                        print("Lo sconosciuto ti dice:")
                        print(opp_choice[1])

                    elif opp_choice[0] == "A":
                        print("Lo sconosciuto sguaina la spada.. Ma inciampa come una pera cotta")

                    elif opp_choice[0] == "R":
                        print("Vieni derubato dallo sconosciuto!")
                        coin_lost = int(player.coin * 0.25)
                        player.coin -= coin_lost
                        conn.sendall(str(coin_lost).encode())

                # Handle "Attack" cases
                elif choice == "a" and player.has_sword:
                    conn.sendall("A:".encode())
                    opp_choice = conn.recv(1024).decode().split(":", 1)

                    if opp_choice[0] == "S":
                        print("Ti prepari ad attacare lo sconosciuto..")
                        print("Ma il Karma punisce le tue cattive intenzioni.")
                        print("Inciampi e perdi parte del tuo bottino.")
                        player.coin = int(player.coin * 0.75)

                    elif opp_choice[0] == "A":
                        print("Lo sconosciuto risponde all'attacco e rimani ferito")
                        player.attacked(1)

                    elif opp_choice[0] == "R":
                        print("Il tuo avversario intendeva derubarti, ma riesci a respingerlo")

                # Handle "Steal" cases
                elif choice == "r" and player.has_knife:
                    conn.sendall("R:".encode())
                    opp_choice = conn.recv(1024).decode().split(":", 1)

                    if opp_choice[0] == "S":
                        print("Riesci a derubare l'ignaro sconosciuto.")
                        player.coin += int(conn.recv(1024).decode())

                    elif opp_choice[0] == "A":
                        print("L'avversario percepisce le tue intenzioni e ti attacca.")
                        player.attacked(2)

                    elif opp_choice[0] == "R":
                        luck = random.randrange(1, 1000)
                        conn.send(str(luck).encode())
                        opp_luck = int(conn.recv(1024).decode())

                        if luck < opp_luck:
                            print("Vieni derubato dallo sconosciuto!")
                            coin_lost = int(player.coin * 0.25)
                            player.coin -= coin_lost
                            conn.sendall(str(coin_lost).encode())

                        elif luck > opp_luck:
                            print("Riesci a derubare lo sconosciuto.")
                            player.coin += int(conn.recv(1024).decode())

                        else:
                            print("Nella foga di derubarvi a vicenda non concludete nulla")

            except ConnectionAbortedError:
                print("L'avversario ha interrotto la connessione")
                multi = False
                dungeon.p2 = None
                conn.close()

        elif room == RM_EMPTY:
            print("Ti immetti nel tetro corridoio...")

        # "Mechanics" rooms cases
        elif room == RM_MNST:
            print("Un mostro orribile ti si para davanti!")

            if player.has_sword:
                print("Usando la tua spada riesci a distruggere il mostro!")
            else:
                player.attacked(1)
                print("Riesci a sconfiggere il mostro, ma subisci dei danni")

            dungeon.set(dungeon.p1, RM_EMPTY)
            msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        elif room == RM_CHEST:
            print("Trovi una cassa del tesoro davanti a te!")

            if player.has_lockpick:
                print("Utilizzando il grimaldello riesci ad aprire la cassa")
                coin_amount = random.randrange(10, 100)
                player.coin += coin_amount

                dungeon.set(dungeon.p1, RM_EMPTY)
                msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

            else:
                print("La cassa è chiusa e non riesci ad aprirla")

        elif room == RM_TRAP:
            print("Questa stanza contiene una trappola!")

            if random.random() < 0.5:
                print("Ti accorgi della trappola e riesci ad evitarla")
            else:
                if player.has_knife:
                    print("Riesci a disinnescare la trappola col tuo coltello")

                elif random.random() < 0.5:
                    player.attacked(2)
                    print("Una nube di gas velenoso ti avvolge")

                else:
                    player.coin = int(player.coin * 0.75)
                    print("Il pavimento si apre sotto ai tuoi piedi.")
                    print("Riesci a metterti in salvo ma parte del tuo bottino cade nel fosso")

            dungeon.set(dungeon.p1, RM_EMPTY)
            msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        elif room == RM_QUIZ:
            print("Sulla parete è riportata una misteriosa incisione...")
            quiz = random.choice(quizzes)
            print(quiz[0])
            ans = input().lower()

            if ans == quiz[1]:
                print("Si apre un'alcova e trovi un tesoro")
                player.coin += random.randrange(10, 100)

            elif random.random() < 0.5:
                player.attacked(2)
                print("Una nube di gas velenoso ti avvolge")

            else:
                player.coin = int(player.coin * 0.75)
                print("Il pavimento si apre sotto ai tuoi piedi.")
                print("Riesci a metterti in salvo ma parte del tuo bottino cade nel fosso")

            dungeon.set(dungeon.p1, RM_EMPTY)
            msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        # Item rooms cases
        elif room == RM_COMP:
            print("Trovi una bussola in questa stanza")

            if player.has_compass:
                print("Ma ne hai già una..")
            else:
                player.has_compass = True
                dungeon.set(dungeon.p1, RM_EMPTY)
                msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        elif room == RM_SWRD:
            print("Trovi una spada in questa stanza")

            if player.has_sword:
                print("Ma ne hai già una..")
            else:
                player.has_sword = True
                dungeon.set(dungeon.p1, RM_EMPTY)
                msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        elif room == RM_KNIFE:
            print("Trovi un coltello in questa stanza")

            if player.has_knife:
                print("Ma ne hai già uno..")
            else:
                player.has_knife = True
                dungeon.set(dungeon.p1, RM_EMPTY)
                msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        elif room == RM_LOCKP:
            print("Trovi un grimaldello in questa stanza")

            if player.has_lockpick:
                print("Ma ne hai già uno..")
            else:
                player.has_lockpick = True
                dungeon.set(dungeon.p1, RM_EMPTY)
                msg_queue.append(MSG_CLR + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

        # Other cases
        elif room == RM_EXIT:
            escaped = True

            if multi:
                msg_queue.append(MSG_ESC + " " + str(player.coin))   # Send escape message and Gold amount

                if not opponent_escaped:  # First player to get out, must wait
                    wait_opponent = True
                else:
                    print("Sei fuggito in tempo!")    # Second player to get out

        else:
            print("C'è qualcosa in questa stanza, ma non riesci a capire cosa...")

        if not escaped:
            if exit_found:
                print("Vedi l'uscita di fronte a te!")

            if turnback:
                turnback = False
                curr_tile = previous_tile
                input("Decidi di tornare indietro... (premi un tasto)")
            else:
                previous_tile, curr_tile = move(curr_tile, conn, dungeon, player)
            dungeon.p1 = curr_tile

            if opponent_escaped and (movs_to_esc < 10):  # Opponent got out, only 10 moves left
                movs_to_esc += 1

                if movs_to_esc == 10:
                    print("Senti la porta chiudersi in lontananza, intrappolandoti per sempre...")
                    player.attacked(player.health)  # DEAD X_X

        if multi:
            try:
                # Queueing my position
                msg_queue.append(MSG_POS + " " + str(dungeon.p1[0]) + " " + str(dungeon.p1[1]))

                # Queueing whether I'm dead
                if not player.attacked(0):
                    msg_queue.append(MSG_DIE)

                # Sending all pending messages
                msg = ""
                for strs in msg_queue:
                    msg += strs + " "
                conn.sendall(msg.encode())

                # Receiving opponent data
                print("Attendi la mossa del tuo avversario...")

                while not (opponent_escaped or opponent_dead):
                    msg = conn.recv(1024).decode()
                    # print(msg) # <--- debug
                    msg = msg.split(' ')

                    for i in range(len(msg)):
                        if msg[i] == MSG_POS:
                            dungeon.p2 = int(msg[i+1]), int(msg[i+2])
                        elif msg[i] == MSG_ESC:
                            opponent_escaped = True  # First player got out
                            opponent_gold = int(msg[i+1])
                            break
                        elif msg[i] == MSG_DIE:
                            opponent_dead = True
                            dungeon.p2 = None
                            conn.close()
                            multi = False
                            break
                        elif msg[i] == MSG_CLR:
                            dungeon.set((int(msg[i+1]), int(msg[i+2])), RM_EMPTY)
                            break

                    # Keep receiving if you are waiting the opponent and said opponent didn't die yet.
                    # All I wanted was a DO - WHILE.
                    if not wait_opponent:
                        break

            except ConnectionAbortedError:
                print("Connessione chiusa da parte dell'avversario")
                multi = False
                dungeon.p2 = None
                conn.close()

        if not player.attacked(0):
            print("Sei morto.")
            break

    # END GAME LOOP #

    if conn is not None:
        conn.close()

    if player.attacked(0):
        print("Riesci finalmente a vedere la luce del giorno. Congratulazioni!")
        if opponent_gold != -1:
            print("Il tuo avversario ha raccimolato ben " + str(opponent_gold) + " monete d'oro.")
            print("Hai raccimolato ben " + str(player.coin) + " monete d'oro.")
            if opponent_gold > player.coin:
                print("Il tuo avversario vince!")
            else:
                print("Hai vinto!")

    input("Premi un tasto per uscire...")

#############
#    RUN    #
#############

play()

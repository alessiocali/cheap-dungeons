import random
import socket as sck

#####################################################################################################################
#       IMPORTANT NOTE                                                                                              #
#####################################################################################################################
#   Throughout the file x and y symbols are used to refer to elements within the grid. These ARE NOT intended to be #
#   x = abscissa / y = ordinate. NOPE. Rather x = row, y = column. I know, I know. It's counter-intuitive. But it   #
#   is due to how the grid is accessed (if I print data[i][j] in a double i,j loop it will first access each row    #
#   and then its subsequent elements). Deal with it.                                                                #
#####################################################################################################################

DUNGEON_SIZE = 25  # Dungeon grid size per side
DUNGEON_SIGHT = 6  # Player is shown nearby [x - sight, x + sight] x [y - sight, y + sight] cells
STUP_DST = 10  # The minimum distance between players and exit during setup
CORRIDOR_BIAS = 0.4  # The probability by which the drunken path will go straight
CORRIDOR_CM_BIAS = (1 - CORRIDOR_BIAS) / 3  # Complementary corridor bias. The probability of all other sides.
DRUNK_LIMIT = 200  # The max number of cell explorable during drunken walk
DRUNK_CHANCE = 0.3  # The probability that when connecting a cell and the exit, a drunken walk will be performed

PC_MNST = 0.05  # Percentage of monsters over the free cells
PC_TRAP = 0.05  # Percentage of traps
PC_QUIZ = 0.025  # Percentage of traps
PC_CHEST = 0.05  # Percentage of chests

RM_WALL = ' # '  # All the map symbols
RM_EMPTY = '   '
RM_PLAYER = ' @ '
RM_EXIT = ' E '
RM_MNST = ' m '
RM_TRAP = ' t '
RM_QUIZ = ' q '
RM_CHEST = ' c '
RM_UNKNW = ' ? '

RM_KNIFE = ' k '
RM_LOCKP = ' l '
RM_COMP = ' C '
RM_SWRD = ' s '


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

        # Spawn random exit distant at least STUP_DST
        while True:
            self.exit = random_coord()
            if tpl_dst(self.p1, self.exit) > STUP_DST:
                self.set(self.exit, RM_EXIT)
                break

        # On multiplayer mode, spawn random P2
        if multi:
            while True:
                self.p2 = random_coord()
                if tpl_dst(self.p1, self.p2) > STUP_DST and tpl_dst(self.exit, self.p2) > STUP_DST:
                    self.set(self.p2, RM_EMPTY)
                    break

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
                symbol = RM_PLAYER if (i, j) in (self.p1, self.p2) else self.get((i, j))
                print("|" + symbol, end="", flush=True)
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
                        subrow += [RM_PLAYER] if (i, j) in (self.p1, self.p2) \
                            else [self.data[i][j]] if (i, j) in player_info.discovered else [RM_UNKNW]
                submatrix += [subrow]

        size = len(submatrix)

        # Print the submatrix. Similar to print() method
        print(" " + "--- " * size)
        for i in range(0, size):
            for j in range(0, size):
                print("|" + submatrix[i][j], end="", flush=True)
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
            sword = "Sì" if player_info.has_lockpick else "Nessuna"
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

            # Pick a random direction, favoring the last one
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
                    seq += [next_pos]  # Add next position to sequence
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
    def unravel_path(self, start, goal):
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

            if self.get(current) != RM_PLAYER:  # Empty the current cell
                self.set(current, RM_EMPTY)
            if random.random() < DRUNK_CHANCE:  # By DRUNK_CHANCE, do a Drunken Walk from the current cell
                self.drunk_path(current, DRUNK_LIMIT / 10)

    # Use drunken walk + unravel to connect start and goal
    def drunken_star(self, start, goal):
        dr_path = self.drunk_path(start, DRUNK_LIMIT)
        connect_start = dr_path[random.randint(0, len(dr_path) - 1)]
        self.unravel_path(connect_start, goal)

    # Get all empty cells as (x, y) tuples. Exclude player cells.
    def get_empty(self):
        return [(i, j) for i in range(0, DUNGEON_SIZE) for j in range(0, DUNGEON_SIZE) if
                self.data[i][j] == RM_EMPTY and (i, j) not in (self.p1, self.p2)]

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
    coin = 0
    discovered = set([])
    has_lockpick = False
    has_knife = False
    has_sword = False
    has_compass = False

    def attacked(self, health_lost):
        self.health = self.health - health_lost if self.health > health_lost else 0
        return self.health != 0

    def lose_coin(self, coin_lost):
        self.coin = self.coin - coin_lost if self.coin > coin_lost else 0

    def discover(self, new):
        self.discovered |= new


# Spit a random coordinate except borders.
def random_coord():
    return random.randint(1, DUNGEON_SIZE - 2), random.randint(1, DUNGEON_SIZE - 2)


# Distance between coordinates is defined by taxi-geometry rather then euclidean
def tpl_dst(a, b):
    x1, y1 = a
    x2, y2 = b
    return abs(x1 - x2) + abs(y1 - y2)


def before(ta, tb):
    return ta[0] < tb[0] and ta[1] < tb[1]


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


def move(curr_tile, socket, dungeon):
    x, y, nx, ny = None, None, None, None

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
        elif pl_input == "esci":
            if socket is not None:
                socket.close()
            exit()
        elif pl_input == "brighteyes":  # Cheat for printing the whole map
            dungeon.print()
            continue
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
    print("Vuoi giocare in solo o con un amico? s/a")
    multi = input() == "a"

    dungeon = DungeonGraph(multi)
    player = Player()

    print("Senza ricordare il perché, ti ritrovi in un luogo a te non familiare...")
    print("Qual è il tuo nome?")

    player.name = input()
    conn = None
    curr_tile = dungeon.p1

    if multi:
        print("Desideri iniziare una nuova partita o connetterti ad una già esistente? n/c")
        type_mod = input()

        if type_mod == "c":
            conn = sck.socket()
            conn.connect(("localhost", 12345))
            msg = "DUNGEON"

            for i in range(DUNGEON_SIZE):
                for j in range(DUNGEON_SIZE):
                    conn.sendall(msg.encode())
                    dungeon.set((i, j), conn.recv(1024).decode())

            # Receive P1 and P2
            pos_string = conn.recv(1024).decode()
            pos_p1 = pos_string.split(',')

            conn.sendall(msg.encode())
            pos_string = conn.recv(1024).decode()
            pos_p2 = pos_string.split(',')

            dungeon.p2 = int(pos_p1[0]), int(pos_p1[1])  # Positions are swapped because this is the second player
            dungeon.p1 = int(pos_p2[0]), int(pos_p2[1])

            curr_tile = dungeon.p1

        else:
            c = sck.socket()  # Connection setup
            c.bind(("localhost", 12345))
            c.listen()
            conn, _ = c.accept()
            c.close()

            for i in range(DUNGEON_SIZE):
                for j in range(DUNGEON_SIZE):
                    msg = conn.recv(1024).decode()
                    if msg == "DUNGEON":
                        conn.sendall(dungeon.get((i, j)).encode())

            pos_string_p1 = str(dungeon.p1[0]) + ',' + str(dungeon.p1[1])
            pos_string_p2 = str(dungeon.p2[0]) + ',' + str(dungeon.p2[1])

            conn.sendall(pos_string_p1.encode())
            err = conn.recv(1024).decode()

            if err == "DUNGEON":
                conn.sendall(pos_string_p2.encode())

            curr_tile = dungeon.p1

    while True:
        room, curr_tile, exit_found = update(curr_tile, player, dungeon)

        if dungeon.p1 == dungeon.p2:
            print("Di fronte a te si staglia uno sconosciuto...")
        elif room == RM_EMPTY:
            print("Ti immetti nel tetro corridoio...")
        elif room == RM_MNST:
            print("Un mostro orribile ti si para davanti!")
        elif room == RM_CHEST:
            print("Trovi una cassa del tesoro davanti a te!")
        elif room == RM_TRAP:
            print("Questa stanza contiene una trappola!")
        elif room == RM_QUIZ:
            print("Sulla parete è riportata una misteriosa incisione...")
        elif room == RM_EXIT:
            break
        else:
            print("C'è qualcosa in questa stanza, ma non riesci a capire cosa...")
        if exit_found:
            print("Vedi l'uscita di fronte a te!")

        previous_tile, curr_tile = move(curr_tile, conn, dungeon)
        dungeon.p1 = curr_tile

        if multi:
            # Sending my position
            pos_string = str(dungeon.p1[0]) + ',' + str(dungeon.p1[1])
            conn.sendall(pos_string.encode())

            # Receiving opponent position
            print("Attendi la mossa del tuo avversario...")
            pos_string = conn.recv(1024).decode()
            pos = pos_string.split(',')
            dungeon.p2 = int(pos[0]), int(pos[1])

    if conn is not None:
        conn.close()

    print("Riesci finalmente a vedere la luce del giorno. Congratulazioni!")
    input("Premi un tasto per uscire...")


#############
#    RUN    #
#############

play()

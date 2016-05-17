import random

DUNGEON_SIZE = 25
DUNGEON_SIGHT = 6
STUP_DST = 10
CORRIDOR_BIAS = 0.4
CORRIDOR_CM_BIAS = (1 - CORRIDOR_BIAS) / 3
DRUNK_LIMIT = 200
DRUNK_CHANCE = 0.3

PC_MNST = 0.05
PC_TRAP = 0.05
PC_QUIZ = 0.025
PC_CHEST = 0.05

RM_WALL = ' # '
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


class DungeonGraph:
    data = []
    p1 = None
    exit = None
    p2 = None

    def __init__(self, multi):
        # Generate empty
        for i in range(0, DUNGEON_SIZE):
            self.data += [[]]
            for j in range(0, DUNGEON_SIZE):
                self.data[i] += [RM_WALL]

        random.seed()
        self.p1 = random_coord()
        self.set(self.p1, RM_PLAYER)

        while True:
            self.exit = random_coord()
            if tpl_dst(self.p1, self.exit) > STUP_DST:
                self.set(self.exit, RM_EXIT)
                break

        if multi:
            while True:
                self.p2 = random_coord()
                if tpl_dst(self.p1, self.p2) > STUP_DST and tpl_dst(self.exit, self.p2) > STUP_DST:
                    self.set(self.p2, RM_PLAYER)
                    break

        self.drunken_star(self.p1, self.exit)

        if multi:
            self.drunken_star(self.p1, self.p2)
            self.drunken_star(self.exit, self.p2)

        empties = self.get_empty()
        empties_len = len(empties)

        mnst_count = int(empties_len * PC_MNST)
        trap_count = int(empties_len * PC_TRAP)
        quiz_count = int(empties_len * PC_QUIZ)
        chest_count = int(empties_len * PC_CHEST)

        knives_count = random.randint(1, 2)
        swords_count = random.randint(1, 2)

        symbols = (RM_MNST, RM_TRAP, RM_QUIZ, RM_CHEST, RM_KNIFE, RM_SWRD, RM_COMP, RM_LOCKP)
        counts = (mnst_count, trap_count, quiz_count, chest_count, knives_count, swords_count, 1, 2)

        for s, c in [(symbols[i], counts[i]) for i in range(0, 8)]:
            self.place(s, c, empties)

    def set(self, pos, room):
        self.data[pos[0]][pos[1]] = room

    def get(self, pos):
        return self.data[pos[0]][pos[1]]

    def get_nearby(self, pos):
        nearby = []
        x, y = pos
        if x > 0:
            nearby += [(x-1, y)]
        if x < DUNGEON_SIZE - 1:
            nearby += [(x + 1, y)]
        if y > 0:
            nearby += [(x, y - 1)]
        if y < DUNGEON_SIZE - 1:
            nearby += [(x, y + 1)]
        return nearby

    def print(self):
        print(" " + "--- " * DUNGEON_SIZE)
        for i in range(0, DUNGEON_SIZE):
            for j in range(0, DUNGEON_SIZE):
                print("|" + self.get((i, j)), end="", flush=True)
            print("|")
            print(" " + "--- " * DUNGEON_SIZE)

    def print_hidden(self, pos, radius, disc_set):
        x, y = pos

        if x < radius:
            x = radius
        elif x > DUNGEON_SIZE - radius:
            x = DUNGEON_SIZE - radius

        if y < radius:
            y = radius
        elif y > DUNGEON_SIZE - radius:
            y = DUNGEON_SIZE - radius

        pos = x, y

        submatrix = []

        for i in range(0, DUNGEON_SIZE):
            if x - radius <= i < x + radius:
                subrow = []
                for j in range(0, DUNGEON_SIZE):
                    if y - radius <= j < y + radius:
                        subrow += [self.data[i][j]] if (i, j) in disc_set else [RM_UNKNW]
                submatrix += [subrow]

        size = len(submatrix)

        print(" " + "--- " * size)
        for i in range(0, size):
            for j in range(0, size):
                print("|" + submatrix[i][j], end="", flush=True)
            print("|")
            print(" " + "--- " * size)

    def drunk_path(self, start, limit):
        drunk_count = 0
        pos = start
        dirs = [(0, 1), (-1, 0), (0, -1), (1, 0)]
        most_likely = (0, 1)
        seq = []

        while True:
            # Swap most likely to first index
            idx = dirs.index(most_likely)
            dirs[0], dirs[idx] = dirs[idx], dirs[0]
            rnd = random.random()

            if rnd < CORRIDOR_BIAS:
                cur_dir = dirs[0]
            elif rnd < CORRIDOR_BIAS + CORRIDOR_CM_BIAS:
                cur_dir = dirs[1]
            elif rnd < CORRIDOR_BIAS + 2 * CORRIDOR_CM_BIAS:
                cur_dir = dirs[2]
            else:
                cur_dir = dirs[3]

            next_pos = pos[0] + cur_dir[0], pos[1] + cur_dir[1]

            if before((0, 0), next_pos) and before(next_pos, (DUNGEON_SIZE - 1, DUNGEON_SIZE - 1)):
                next_tile = self.get(next_pos)
                if next_tile == RM_EXIT:
                    break
                elif next_tile == RM_EMPTY or next_tile == RM_WALL:
                    self.set(next_pos, RM_EMPTY)
                    seq += [next_pos]
                    pos = next_pos
                    most_likely = cur_dir
                    drunk_count += 1
                    if drunk_count >= limit:
                        break
                else:
                    continue
            else:
                continue

        return seq

    def unravel_path(self, start, goal):
        current = start
        cx, cy = current
        gx, gy = goal
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

            if self.get(current) != RM_PLAYER:
                self.set(current, RM_EMPTY)
            if random.random() < DRUNK_CHANCE:
                self.drunk_path(current, DRUNK_LIMIT / 10)

    def drunken_star(self, start, goal):
        dr_path = self.drunk_path(start, DRUNK_LIMIT)
        star_start = dr_path[random.randint(0, len(dr_path) - 1)]
        self.unravel_path(star_start, goal)

    def get_empty(self):
        return [(i, j) for i in range(0, DUNGEON_SIZE) for j in range(0, DUNGEON_SIZE) if self.data[i][j] == RM_EMPTY]

    def place(self, symbol, count, empties):
        placed = 0
        while placed < count:
            x, y = random.choice(empties)
            self.data[x][y] = symbol
            empties.remove((x, y))
            placed += 1


class Player:
    name = "???"
    HP_MAX = 10
    COIN_MAX = 9999
    health = 10
    coin = 0
    discovered = set([])

    def attacked(self, health_lost):
        self.health = self.health - health_lost if self.health > health_lost else 0
        return self.health != 0

    def lose_coin(self, coin_lost):
        self.coin = self.coin - coin_lost if self.coin > coin_lost else 0

    def discover(self, new):
        self.discovered = self.discovered | new


def random_coord():
    return random.randint(1, DUNGEON_SIZE - 2), random.randint(1, DUNGEON_SIZE - 2)


def tpl_dst(a, b):
    x1, y1 = a
    x2, y2 = b
    return abs(x1 - x2) + abs(y1 - y2)


def before(ta, tb):
    return ta[0] < tb[0] and ta[1] < tb[1]


#############
# TEST CODE #
#############
"""
dungeon = DungeonGraph(True)
dungeon.print()
input()
"""

dungeon = DungeonGraph(False)
player = Player()

print("Senza ricordare il perché, ti ritrovi in un luogo a te non familiare...")
print("Qual è il tuo nome?")
player.name = input()

previous_tile = None
next_tile = dungeon.p1
exit_found = False

while True:
    x, y = next_tile

    if previous_tile is not None:
        dungeon.set(previous_tile, RM_EMPTY)

    room = dungeon.get(next_tile)

    dungeon.set(next_tile, RM_PLAYER)

    newly_discovered = set([next_tile])

    for near_pos in dungeon.get_nearby(next_tile):
        next_room = dungeon.get(near_pos)
        if next_room == RM_WALL or next_room == RM_EXIT or next_room == RM_EMPTY:
            exit_found = next_room == RM_EXIT
            newly_discovered |= set([near_pos])

    player.discover(newly_discovered)

    dungeon.print_hidden(next_tile, DUNGEON_SIGHT, player.discovered)

    if exit_found:
        print("Vedi l'uscita di fronte a te!")
        exit_found = False

    if room == RM_EMPTY:
        print("Ti immetti nel tetro corridoio...")
    elif room == RM_MNST:
        print("Un mostro orribile ti si para davanti!")
    elif room == RM_EXIT:
        break
    else :
        print("C'è qualcosa in questa stanza, ma non riesci a capire cosa...")

    while True:
        print("Dove desideri andare?")
        dir = input()
        nx, ny = x, y

        if dir == 'w':
            nx = x - 1
        elif dir == 'a':
            ny = y - 1
        elif dir == 's':
            nx = x + 1
        elif dir == 'd':
            ny = y + 1
        elif dir == '':
            print("Decidi di restare qui")
        elif dir == "brighteyes":
            dungeon.print()
            continue
        else:
            print("Input non riconosciuto.")
            continue
        if dungeon.get((nx, ny)) == RM_WALL:
            print("Vi è un muro in quella direzione.")
            continue
        break

    previous_tile = next_tile
    next_tile = nx, ny

print("Riesci finalmente a vedere la luce del giorno. Congratulazioni!")
input("Premi un tasto per uscire...")
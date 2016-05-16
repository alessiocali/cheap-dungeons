import random
import heapq

DUNGEON_SIZE = 50
STUP_DST = 10
CORRIDOR_BIAS = 0.4
CORRIDOR_CM_BIAS = (1 - CORRIDOR_BIAS) / 3
DRUNK_LIMIT = 200
DRUNK_CHANCE = 0.3

PC_MNST = 0.05
PC_TRAP = 0.05
PC_QUIZ = 0.025
PC_CHEST = 0.05

RM_WALL = '#'
RM_EMPTY = '.'
RM_PLAYER = '@'
RM_EXIT = 'ò'
RM_MNST = 'm'
RM_TRAP = 't'
RM_QUIZ = 'q'
RM_CHEST = 'c'


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]


class DungeonGraph:
    data = []
    p1 = None
    p2 = None
    exit = None

    def __init__(self):
        # Generate empty
        for i in range(0, DUNGEON_SIZE):
            self.data += [[]]
            for j in range(0, DUNGEON_SIZE):
                self.data[i] += [RM_WALL]

        random.seed()
        self.p1 = random_coord()
        self.set(self.p1, RM_PLAYER)

        while True:
            self.p2 = random_coord()
            if tpl_dst(self.p1, self.p2) < STUP_DST:
                continue
            else:
                self.set(self.p2, RM_PLAYER)
                break

        while True:
            self.exit = random_coord()
            if tpl_dst(self.p1, self.exit) < STUP_DST or tpl_dst(self.p2, self.exit) < STUP_DST:
                continue
            else:
                self.set(self.exit, RM_EXIT)
                break

        self.drunken_star(self.p1, self.exit)
        self.drunken_star(self.p2, self.exit)
        self.drunken_star(self.p1, self.p2)

        empties = self.get_empty()
        empties_len = len(empties)

        mnst_count = int(empties_len * PC_MNST)
        trap_count = int(empties_len * PC_TRAP)
        quiz_count = int(empties_len * PC_QUIZ)
        chest_count = int(empties_len * PC_CHEST)

        symbols = (RM_MNST, RM_TRAP, RM_QUIZ, RM_CHEST)
        counts = (mnst_count, trap_count, quiz_count, chest_count)

        for s, c in [(symbols[i], counts[i]) for i in range(0, 4)]:
            self.place(s, c, empties)

    def set(self, pos, room):
        self.data[pos[0]][pos[1]] = room

    def get(self, pos):
        return self.data[pos[0]][pos[1]]

    def neighbors(self, pos):
        neigh = []
        x,y = pos
        if x > 0:
            neigh += [(x-1,y)]
        if x < DUNGEON_SIZE - 1:
            neigh += [(x+1,y)]
        if y > 0:
            neigh += [(x,y-1)]
        if y < DUNGEON_SIZE - 1:
            neigh += [(x,y+1)]
        return neigh

    def print(self):
        for i in range(0, DUNGEON_SIZE):
            for j in range(0, DUNGEON_SIZE):
                print(dungeon.get((i, j)), end="", flush=True)
            print("")

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
                    if drunk_count >= limit: break
                else:
                    continue
            else:
                continue

        return seq

    def a_star_search(self, start, goal):
        frontier = PriorityQueue()
        frontier.put(start, 0)
        came_from = {}
        cost_so_far = {}
        came_from[start] = None
        cost_so_far[start] = 0

        while not frontier.empty():
            current = frontier.get()

            if current == goal:
                break

            for next in self.neighbors(current):
                new_cost = cost_so_far[current] + 1
                if next not in cost_so_far or new_cost < cost_so_far[next]:
                    cost_so_far[next] = new_cost
                    priority = new_cost + tpl_dst(goal, next)
                    frontier.put(next, priority)
                    came_from[next] = current

        return came_from

    def unravel_path(self, a_star_chain, goal):
        current = goal
        while (True):
            current = a_star_chain[current]
            if current is None: break
            else:
                if (self.get(current) != RM_PLAYER):
                    self.set(current, RM_EMPTY)
                if (random.random() < DRUNK_CHANCE):
                    self.drunk_path(current, DRUNK_LIMIT / 10)

    def drunken_star(self, start, goal):
        dr_path = self.drunk_path(start, DRUNK_LIMIT)
        star_start = dr_path[random.randint(0, len(dr_path) - 1)]
        a_star = self.a_star_search(star_start, goal)
        self.unravel_path(a_star, goal)

    def get_empty(self):
        return [(i, j) for i in range(0, DUNGEON_SIZE) for j in range(0, DUNGEON_SIZE) if self.data[i][j] == RM_EMPTY]

    def place(self, symbol, count, empties):
        placed = 0
        while placed < count:
            x, y = random.choice(empties)
            self.data[x][y] = symbol
            empties.remove((x, y))
            placed += 1


def random_coord():
    return random.randint(1, DUNGEON_SIZE - 2), random.randint(1, DUNGEON_SIZE - 2)


def tpl_dst(a,b):
    x1,y1 = a
    x2,y2 = b
    return abs(x1-x2) + abs(y1-y2)


def before(ta, tb):
    return ta[0] < tb[0] and ta[1] < tb[1]

#######
#CODE #
#######
dungeon = DungeonGraph()
dungeon.print()
input()
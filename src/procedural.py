import random
import heapq

DUNGEON_SIZE = 50
STUP_DST = 30
CORRIDOR_BIAS = 0.4
CORRIDOR_CM_BIAS = (1 - CORRIDOR_BIAS) / 3
DRUNK_LIMIT = 200
DRUNK_CHANCE = 0.3

RM_WALL = '#'
RM_EMPTY = '.'
RM_PLAYER = '@'
RM_EXIT = 'ò'


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

    def set(self, pos, room):
        self.data[pos[0]][pos[1]] = room

    def get(self, pos):
        return self.data[pos[0]][pos[1]]

    def neighbors(self, pos):
        neigh = []
        x,y = pos
        if (x > 0): neigh += [(x-1,y)]
        if (x < DUNGEON_SIZE - 1): neigh += [(x+1,y)]
        if (y > 0): neigh += [(x,y-1)]
        if (y < DUNGEON_SIZE - 1): neigh += [(x,y+1)]
        return neigh


def random_coord():
    return random.randint(0, DUNGEON_SIZE - 1), random.randint(0, DUNGEON_SIZE - 1)


def print_dungeon():
    for i in range(0, DUNGEON_SIZE):
        for j in range (0, DUNGEON_SIZE):
            print(dungeon.get((i,j)),end="",flush=True)
        print("")


def tpl_dst(a,b):
    x1,y1 = a
    x2,y2 = b
    return abs(x1-x2) + abs(y1-y2)


def before(ta, tb):
    return ta[0] < tb[0] and ta[1] < tb[1]


def drunk_path(player, limit):
    drunk_count = 0
    pos = player
    dirs = [(0, 1), (-1, 0), (0, -1), (1, 0)]
    most_likely = (0, 1)
    seq = []

    while (True):
        # Swap most likely to first index
        idx = dirs.index(most_likely)
        dirs[0], dirs[idx] = dirs[idx], dirs[0]
        rnd = random.random()

        if (rnd < CORRIDOR_BIAS):
            dir = dirs[0]
        elif (rnd < CORRIDOR_BIAS + CORRIDOR_CM_BIAS):
            dir = dirs[1]
        elif (rnd < CORRIDOR_BIAS + 2 * CORRIDOR_CM_BIAS):
            dir = dirs[2]
        else:
            dir = dirs[3]

        next = pos[0] + dir[0], pos[1] + dir[1]

        if (before((0, 0), next) and before(next, (DUNGEON_SIZE - 1, DUNGEON_SIZE - 1))):
            next_tile = dungeon.get(next)
            if (next_tile == RM_EXIT):
                break
            elif (next_tile == RM_EMPTY or next_tile == RM_WALL):
                dungeon.set(next, RM_EMPTY)
                seq += [next]
                pos = next
                most_likely = dir
                drunk_count += 1
                if (drunk_count >= limit): break
            else:
                continue
        else:
            continue

    return seq


def a_star_search(graph, start, goal):
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

        for next in graph.neighbors(current):
            new_cost = cost_so_far[current] + 1
            if next not in cost_so_far or new_cost < cost_so_far[next]:
                cost_so_far[next] = new_cost
                priority = new_cost + tpl_dst(goal, next)
                frontier.put(next, priority)
                came_from[next] = current

    return came_from


def unravel_path(a_star_chain, goal):
    current = goal
    while (True):
        current = a_star_chain[current]
        if current is None: break
        else:
            if (dungeon.get(current) != RM_PLAYER):
                dungeon.set(current, RM_EMPTY)
            if (random.random() < DRUNK_CHANCE):
                drunk_path(current, DRUNK_LIMIT / 10)


def drunken_star(start, dun):
    dr_path = drunk_path(start, DRUNK_LIMIT)
    star_start = dr_path[random.randint(0, len(dr_path) - 1)]
    a_star = a_star_search(dun, star_start, dun.exit)
    unravel_path(a_star, dun.exit)

#######
#CODE #
#######

random.seed()

dungeon = DungeonGraph()

#Startup
dungeon.p1 = random_coord()
dungeon.set(dungeon.p1, RM_PLAYER)

while(True):
    dungeon.p2 = random_coord()
    if (tpl_dst(dungeon.p1, dungeon.p2) < STUP_DST): continue
    else:
        dungeon.set(dungeon.p2, RM_PLAYER)
        break

while(True):
    dungeon.exit = random_coord()
    if (tpl_dst(dungeon.p1, dungeon.exit) < STUP_DST or tpl_dst(dungeon.p2, dungeon.exit) < STUP_DST): continue
    else:
        dungeon.set(dungeon.exit, RM_EXIT)
        break

drunken_star(dungeon.p1, dungeon)
drunken_star(dungeon.p2, dungeon)

print_dungeon()


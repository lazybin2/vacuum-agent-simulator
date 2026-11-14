from collections import deque
import heapq
import itertools
import random


class VacuumEnvironment:
    """Grid codes: 0 = clean, 1 = dirt, 2 = wall, 3 = power station, 4 = hazard."""

    def __init__(
        self,
        size=5,
        dirt_probability=0.2,
        wall_probability=0.15,
        num_agents=1,
        enable_battery=True,
        seed=None,
    ):
        self.size = size
        self.num_agents = num_agents
        self.enable_battery = enable_battery
        self.rng = random.Random(seed if seed else None)

        # Static hazard (bottom-left corner)
        self.static_hazard = (size - 1, 0)

        # Power stations spread over DIFFERENT sides of the grid
        self.dock_positions = self._make_dock_layout()

        self.visited_trail = set()   # every cell an agent has walked on
        self.swept_cells = set()     # ONLY cells that were dirty and got cleaned
        self.targets = {}      # agent id -> dirt cell it is heading to
        self.ticks = 0         # simulation clock (used as a safety limit)
        self.logged = False    # result already saved to the database?

        self._build_world(dirt_probability, wall_probability)


    # World generation
    def _make_dock_layout(self):
        s = self.size
        mid = s // 2
        layout = [
            (mid, 0),          # LEFT side
            (0, s - 1),        # TOP-RIGHT corner
            (s - 1, mid),      # BOTTOM side
        ]
        if s >= 8:
            layout.append((0, mid))  # TOP side (bigger grids get a 4th station)

        docks = []
        for d in layout:
            if d != self.static_hazard and d not in docks:
                docks.append(d)
        return docks

    def _flood_fill(self, grid, start):
        s = self.size
        seen = {start}
        queue = deque([start])
        while queue:
            r, c = queue.popleft()
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if (
                    0 <= nr < s
                    and 0 <= nc < s
                    and (nr, nc) not in seen
                    and grid[nr][nc] not in (2, 4)
                ):
                    seen.add((nr, nc))
                    queue.append((nr, nc))
        return seen

    def _build_world(self, dirt_probability, wall_probability):
        s = self.size
        grid = spawns = reachable = None

        # Re-generate until agents, power stations and dirt are all connected.
        # The wall density shrinks every attempt, so the loop always ends
        # (at attempt 200 there are no walls at all = always valid).
        for attempt in range(250):
            p = wall_probability * max(0.0, 1.0 - attempt / 200.0)
            grid = [[0 for _ in range(s)] for _ in range(s)]
            grid[self.static_hazard[0]][self.static_hazard[1]] = 4
            for dr, dc in self.dock_positions:
                grid[dr][dc] = 3

            for r in range(s):
                for c in range(s):
                    if (
                        (r, c) in self.dock_positions
                        or (r, c) == self.static_hazard
                        or (r, c) == (0, 0)
                    ):
                        continue
                    if self.rng.random() < p:
                        grid[r][c] = 2

            # Agents start on the first free cells (never on a wall/dock/hazard)
            free = [(r, c) for r in range(s) for c in range(s) if grid[r][c] == 0]
            spawns = free[: self.num_agents]
            if len(spawns) < self.num_agents:
                continue

            reachable = self._flood_fill(grid, spawns[0])
            if all(sp in reachable for sp in spawns) and all(
                d in reachable for d in self.dock_positions
            ):
                break

        self.grid = grid

        # Agents
        self.agents = []
        for i, pos in enumerate(spawns):
            self.agents.append({
                "id": i + 1,
                "x": pos[0],
                "y": pos[1],
                "battery": 100,
                "cleaned": 0,
                "steps": 0,
                "status": "Active",
                "wait": 0,
            })

        # Dirt only on cells the agents can really reach
        candidates = sorted(
            cell for cell in reachable
            if grid[cell[0]][cell[1]] == 0 and cell not in spawns
        )
        for r, c in candidates:
            if self.rng.random() < dirt_probability:
                grid[r][c] = 1
        if candidates and not any(1 in row for row in grid):
            r, c = self.rng.choice(candidates)
            grid[r][c] = 1

        self.initial_dirt_count = sum(row.count(1) for row in self.grid)

    def is_clean(self):
        return not any(1 in row for row in self.grid)

    def get_nearest_dock(self, x, y):
        """Straight-line (Manhattan) nearest dock - kept for compatibility."""
        return min(
            self.dock_positions, key=lambda d: abs(d[0] - x) + abs(d[1] - y)
        )


class EnterpriseVacuumAgent:
    LOW_BATTERY = 40       # the classic 40% rule
    MOVE_COST = 2
    RETURN_COST = 4
    CLEAN_COST = 3
    SAFETY_MARGIN = 12     # extra battery kept so the agent never dies far away
    EXPLORE_RATE = 0.15    # random-move chance for the "Q-Learning (RL)" mode
    MAX_WAIT = 3

    def __init__(self, env, algorithm="A*"):
        self.env = env
        self.algorithm = algorithm
        self.nodes_expanded = 0


    # Path-finding (BFS / Dijkstra / A*)
    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _neighbors(self, cell, blocked=None):
        r, c = cell
        size = self.env.size
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if (
                0 <= nr < size
                and 0 <= nc < size
                and self.env.grid[nr][nc] not in (2, 4)
                and (not blocked or (nr, nc) not in blocked)
            ):
                yield (nr, nc)

    @staticmethod
    def _reconstruct(parent, current):
        path = []
        while parent[current] is not None:
            path.append(current)
            current = parent[current]
        path.reverse()
        return path

    def search_path(self, start, goal, blocked=None):
        if self.algorithm == "BFS":
            return self.bfs_search(start, goal, blocked)
        elif self.algorithm == "Dijkstra":
            return self.dijkstra_search(start, goal, blocked)
        # "A* Search" and the base path of "Q-Learning (RL)"
        return self.a_star_search(start, goal, blocked)

    def bfs_search(self, start, goal, blocked=None):
        queue = deque([start])
        parent = {start: None}
        while queue:
            current = queue.popleft()
            self.nodes_expanded += 1
            if current == goal:
                return self._reconstruct(parent, current)
            for nxt in self._neighbors(current, blocked):
                if nxt not in parent:
                    parent[nxt] = current
                    queue.append(nxt)
        return None

    def dijkstra_search(self, start, goal, blocked=None):
        return self.a_star_search(start, goal, blocked, use_heuristic=False)

    def a_star_search(self, start, goal, blocked=None, use_heuristic=True):
        counter = itertools.count()
        open_set = [(0, next(counter), start)]
        g_score = {start: 0}
        parent = {start: None}
        closed = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current in closed:
                continue
            closed.add(current)
            self.nodes_expanded += 1

            if current == goal:
                return self._reconstruct(parent, current)

            for nxt in self._neighbors(current, blocked):
                if nxt in closed:
                    continue
                tentative = g_score[current] + 1
                if tentative < g_score.get(nxt, float("inf")):
                    g_score[nxt] = tentative
                    parent[nxt] = current
                    h = self.heuristic(nxt, goal) if use_heuristic else 0
                    heapq.heappush(open_set, (tentative + h, next(counter), nxt))
        return None

    def q_learning_policy(self, start, goal, blocked=None):
        path = self.a_star_search(start, goal, blocked)
        return self._explore(start, path, blocked)

    def _explore(self, start, path, blocked=None):
        """Epsilon-style random move used only by the Q-Learning (RL) mode."""
        if (
            self.algorithm == "Q-Learning (RL)"
            and path
            and len(path) > 1
            and self.env.rng.random() < self.EXPLORE_RATE
        ):
            valid = list(self._neighbors(start, blocked))
            if valid:
                return [self.env.rng.choice(valid)]
        return path

    
    # Helpers
    def _occupied_by_others(self, agent):
        docks = self.env.dock_positions
        return {
            (a["x"], a["y"])
            for a in self.env.agents
            if a is not agent and (a["x"], a["y"]) not in docks
        }

    def _path(self, start, goal, blocked):
        """Shortest path avoiding other agents (falls back to ignoring them)."""
        if blocked:
            path = self.search_path(start, goal, blocked - {goal})
            if path is not None:
                return path
        return self.search_path(start, goal, None)

    def _closest(self, start, goals, blocked):
        """Run the selected algorithm to every goal, return the shortest one."""
        best_goal, best_path = None, None
        for goal in goals:
            path = self._path(start, goal, blocked)
            if path is not None and (best_path is None or len(path) < len(best_path)):
                best_goal, best_path = goal, path
        return best_goal, best_path

    def _advance(self, agent, path, blocked, cost, explore=True):
        start = (agent["x"], agent["y"])
        if explore:
            path = self._explore(start, path, blocked)
        nxt = path[0]
        if nxt in blocked and agent["wait"] < self.MAX_WAIT:
            # Short wait for another agent to move away. It resets after
            # MAX_WAIT ticks, so two agents can never block each other forever.
            agent["wait"] += 1
            agent["status"] = "Waiting for clear path ⏳"
            return True
        agent["wait"] = 0
        agent["x"], agent["y"] = nxt
        agent["steps"] += 1
        agent["battery"] = max(0, agent["battery"] - cost)
        return True

   
    # One simulation step for one agent
    def step_agent(self, agent):
        env = self.env
        if env.is_clean():
            return False

        pos = (agent["x"], agent["y"])
        env.visited_trail.add(pos)
        blocked = self._occupied_by_others(agent)

        #Battery / Power Station logic (uses BFS / Dijkstra / A*)
        if env.enable_battery:
            if pos in env.dock_positions:
                agent["battery"] = 100
                agent["status"] = "Fully Charged at Power Station 🔋"
            else:
                if agent["battery"] <= 0:
                    agent["status"] = "Battery Empty ❌"
                    return False

                # Run the selected algorithm to EVERY station and pick the
                # one with the shortest real path (walls included).
                dock, route = self._closest(pos, env.dock_positions, blocked)
                if route:
                    needed = min(
                        90, len(route) * self.RETURN_COST + self.SAFETY_MARGIN
                    )
                    if agent["battery"] <= max(self.LOW_BATTERY, needed):
                        env.targets.pop(agent["id"], None)
                        agent["status"] = (
                            f"Returning to Power Station ⚡ ({dock[0] + 1},"
                            f"{dock[1] + 1}) via {self.algorithm}"
                        )
                        # No random exploration while heading to charge
                        return self._advance(
                            agent, route, blocked, self.RETURN_COST,
                            explore=False,
                        )

        #Clean the dirt under the agent
        if env.grid[pos[0]][pos[1]] == 1:
            env.grid[pos[0]][pos[1]] = 0
            env.swept_cells.add(pos)
            env.targets.pop(agent["id"], None)
            agent["cleaned"] += 1
            agent["battery"] = max(0, agent["battery"] - self.CLEAN_COST)
            agent["steps"] += 1
            agent["status"] = "Cleaning 🧹"
            return True

        # ---- Choose the nearest dirt (different agents -> different dirt) ----
        dirts = [
            (r, c)
            for r in range(env.size)
            for c in range(env.size)
            if env.grid[r][c] == 1
        ]
        if not dirts:
            return False

        reserved = {
            t for aid, t in env.targets.items()
            if aid != agent["id"] and env.grid[t[0]][t[1]] == 1
        }
        preferred = [d for d in dirts if d not in reserved]
        others = [d for d in dirts if d in reserved]

        goal, path = self._closest(pos, preferred, blocked)
        if path is None and others:
            goal, path = self._closest(pos, others, blocked)

        if path:
            env.targets[agent["id"]] = goal
            agent["status"] = "Cleaning 🧹"
            return self._advance(agent, path, blocked, self.MOVE_COST)

        return False
from collections import deque
import heapq
import random


class VacuumEnvironment:

  def __init__(self, size=5, dirt_probability=0.2, wall_probability=0.15):
    self.size = size
    self.grid = [[0 for _ in range(size)] for _ in range(size)]
    self.agent_x = 0
    self.agent_y = 0

    for r in range(size):
      for c in range(size):
        if r == 0 and c == 0:
          continue
        rand = random.random()
        if rand < wall_probability:
          self.grid[r][c] = 2  # Wall
        elif rand < wall_probability + dirt_probability:
          self.grid[r][c] = 1  # Dirt 

    self.initial_dirt_count = sum(row.count(1) for row in self.grid)
    self.visited_trail = set()  # track of visited cells for trail visualization

  def is_clean(self):
    return not any(1 in row for row in self.grid)


class AdvancedVacuumAgent:

  def __init__(self, env, algorithm="A*"):
    self.env = env
    self.algorithm = algorithm
    self.total_steps = 0
    self.cleaned_count = 0
    self.history_steps = []  # for analytics: track remaining dirt after each step

  def heuristic(self, a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

  def search_path(self, start, goal):
    if self.algorithm == "BFS":
      return self.bfs_search(start, goal)
    elif self.algorithm == "Dijkstra":
      return self.dijkstra_search(start, goal)
    else:  # A* Search
      return self.a_star_search(start, goal)

  def bfs_search(self, start, goal):
    queue = deque([[start]])
    visited = {start}

    while queue:
      path = queue.popleft()
      current = path[-1]

      if current == goal:
        return path[1:]

      r, c = current
      for nr, nc in [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]:
        if (
            0 <= nr < self.env.size
            and 0 <= nc < self.env.size
            and self.env.grid[nr][nc] != 2
        ):
          if (nr, nc) not in visited:
            visited.add((nr, nc))
            queue.append(path + [(nr, nc)])
    return None

  def dijkstra_search(self, start, goal):
    return self.a_star_search(start, goal, use_heuristic=False)

  def a_star_search(self, start, goal, use_heuristic=True):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {
        (r, c): float("inf")
        for r in range(self.env.size)
        for c in range(self.env.size)
    }
    g_score[start] = 0

    while open_set:
      current = heapq.heappop(open_set)[1]

      if current == goal:
        path = []
        while current in came_from:
          path.append(current)
          current = came_from[current]
        path.reverse()
        return path

      r, c = current
      for nr, nc in [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]:
        if (
            0 <= nr < self.env.size
            and 0 <= nc < self.env.size
            and self.env.grid[nr][nc] != 2
        ):
          tentative_g_score = g_score[current] + 1
          if tentative_g_score < g_score[(nr, nc)]:
            came_from[(nr, nc)] = current
            g_score[(nr, nc)] = tentative_g_score
            h = self.heuristic((nr, nc), goal) if use_heuristic else 0
            f = tentative_g_score + h
            if (nr, nc) not in [i[1] for i in open_set]:
              heapq.heappush(open_set, (f, (nr, nc)))
    return None

  def find_target_path(self):
    start = (self.env.agent_x, self.env.agent_y)
    if self.env.grid[start[0]][start[1]] == 1:
      return [start]

    dirts = [
        (r, c)
        for r in range(self.env.size)
        for c in range(self.env.size)
        if self.env.grid[r][c] == 1
    ]
    if not dirts:
      return []

    best_path = None
    min_cost = float("inf")

    for dirt in dirts:
      path = self.search_path(start, dirt)
      if path is not None and len(path) < min_cost:
        min_cost = len(path)
        best_path = path

    return best_path

  def step(self):
    if self.env.is_clean():
      return False

    curr_x, curr_y = self.env.agent_x, self.env.agent_y

    # Track the agent's trail for visualization
    self.env.visited_trail.add((curr_x, curr_y))

    if self.env.grid[curr_x][curr_y] == 1:
      self.env.grid[curr_x][curr_y] = 0
      self.cleaned_count += 1
      remaining = sum(row.count(1) for row in self.env.grid)
      self.history_steps.append(
          {"Step": self.total_steps, "Remaining Dirt": remaining}
      )
      return True

    path = self.find_target_path()
    if path:
      next_pos = path[0]
      self.env.agent_x, self.env.agent_y = next_pos
      self.total_steps += 1
      remaining = sum(row.count(1) for row in self.env.grid)
      self.history_steps.append(
          {"Step": self.total_steps, "Remaining Dirt": remaining}
      )
      return True

    return False
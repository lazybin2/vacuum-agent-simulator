import random
class VacuumEnvironment:

    # advanced environment with a grid and dirt probability
    def __init__(self, size=5, dirt_probability=0.3):
        self.size = size
        self.grid = [
            [
                1 if random.random() < dirt_probability else 0
                for _ in range(size)
            ]
            for _ in range(size)
        ]
        self.agent_x = 0
        self.agent_y = 0
        self.grid[0][0] = 0  # Start position is always clean
        self.initial_dirt_count = sum(row.count(1) for row in self.grid)

    def is_clean(self):
        # Check if the environment is clean (no dirt left)
        return not any(1 in row for row in self.grid)


class GoalBasedVacuumAgent:
    # Goal-based agent that uses A* search to find the nearest dirt and clean it

    def __init__(self, env):
        self.env = env
        self.total_steps = 0
        self.cleaned_count = 0
        self.path_history = []

    def find_nearest_dirt_astar(self):
        """A* Heuristic (Manhattan Distance) to find the nearest dirt"""
        start = (self.env.agent_x, self.env.agent_y)
        if self.env.grid[start[0]][start[1]] == 1:
            return start

        dirts = []
        for r in range(self.env.size):
            for c in range(self.env.size):
                if self.env.grid[r][c] == 1:
                    dirts.append((r, c))

        if not dirts:
            return None

        # A* Cost Function: f(n) = g(n) + h(n)
        # here g(n) is the distance from the agent to the dirt, and h(n) is the Manhattan distance
        best_target = min(
            dirts,
            key=lambda d: abs(self.env.agent_x - d[0])
            + abs(self.env.agent_y - d[1]),
        )
        return best_target

    def step(self):
        # Agent takes a step in the environment
        if self.env.is_clean():
            return False

        curr_x, curr_y = self.env.agent_x, self.env.agent_y

        # if the current position has dirt, clean it
        if self.env.grid[curr_x][curr_y] == 1:
            self.env.grid[curr_x][curr_y] = 0
            self.cleaned_count += 1
            return True

        # a* logic to find the nearest dirt and move towards it
        target_pos = self.find_nearest_dirt_astar()
        if target_pos:
            target_x, target_y = target_pos
            if curr_x < target_x:
                self.env.agent_x += 1
            elif curr_x > target_x:
                self.env.agent_x -= 1
            elif curr_y < target_y:
                self.env.agent_y += 1
            elif curr_y > target_y:
                self.env.agent_y -= 1

            self.total_steps += 1
            self.path_history.append((self.env.agent_x, self.env.agent_y))
            return True

        return False
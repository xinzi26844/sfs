import random
import math
from collections import defaultdict, deque

# 课程数据
courses = [
    {"name": "结构力学", "day": 0, "difficulty": 3, "credit": 2},  # 周一=0
    {"name": "理论力学", "day": 1, "difficulty": 4, "credit": 2},  # 周二=1
    {"name": "体育", "day": 1, "difficulty": 1, "credit": 1},  # 周二=1
    {"name": "土木工程实验", "day": 2, "difficulty": 2, "credit": 1},  # 周三=2
    {"name": "结构力学", "day": 3, "difficulty": 3, "credit": 2},  # 周四=3
    {"name": "马克思主义原理", "day": 4, "difficulty": 2, "credit": 3},  # 周五=4
    {"name": "数据结构", "day": 4, "difficulty": 4, "credit": 1.5}  # 周五=4
]
days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
n_courses = len(courses)

class Particle:
    def __init__(self):
        self.position = [(random.randint(0, 6), random.uniform(0.5, 3)) for _ in range(n_courses)]
        self.velocity = [(random.uniform(-1, 1), random.uniform(-1, 1)) for _ in range(n_courses)]
        self.best_position = self.position[:]
        self.objectives = None
        self.best_objectives = None

    def evaluate(self):
        # 目标1: 总时间偏离8小时的程度
        total_time = sum(dur for _, dur in self.position)
        f1 = abs(total_time - 8)

        # 目标2: 记忆效率(基于遗忘曲线)
        mem_eff = 0
        for i in range(n_courses):
            start_time, _ = self.position[i]
            delay = start_time - courses[i]["day"]
            if delay >= 0:
                mem_eff += courses[i]["credit"] * (0.7 ** delay)

        # 目标3: 疲劳度(基于每日作业时间分布)
        daily_hours = defaultdict(float)
        for start_time, dur in self.position:
            daily_hours[start_time] += dur
        if daily_hours:
            avg = sum(daily_hours.values()) / len(daily_hours)
            f3 = math.sqrt(sum((h - avg) ** 2 for h in daily_hours.values()) / len(daily_hours))
        else:
            f3 = 0

        # 目标4: 作业质量(基于难度和时间分配)
        quality = 0
        for i in range(n_courses):
            _, duration = self.position[i]
            quality += min(1, duration / courses[i]["difficulty"]) * courses[i]["credit"]

        self.objectives = (f1, -mem_eff, f3, -quality)  # 注意需要最小化的目标
        if self.best_objectives is None or self.dominates(self.objectives, self.best_objectives):
            self.best_position = self.position[:]
            self.best_objectives = self.objectives

    def dominates(self, obj1, obj2):
        not_worse = all(x <= y for x, y in zip(obj1, obj2))
        strictly_better = any(x < y for x, y in zip(obj1, obj2))
        return not_worse and strictly_better

class MOPSO:
    def __init__(self, pop_size=50, max_gen=100, w=0.5, c1=1.5, c2=1.5):
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.w = w  # 惯性权重
        self.c1 = c1  # 认知常数
        self.c2 = c2  # 社会常数
        self.swarm = [Particle() for _ in range(self.pop_size)]
        self.archive = deque(maxlen=100)  # 非支配解存档

    def update_velocity(self, particle, global_best):
        for i in range(n_courses):
            r1, r2 = random.random(), random.random()
            cognitive = self.c1 * r1 * (particle.best_position[i][0] - particle.position[i][0]), self.c1 * r1 * (particle.best_position[i][1] - particle.position[i][1])
            social = self.c2 * r2 * (global_best.position[i][0] - particle.position[i][0]), self.c2 * r2 * (global_best.position[i][1] - particle.position[i][1])
            particle.velocity[i] = (self.w * particle.velocity[i][0] + cognitive[0] + social[0], self.w * particle.velocity[i][1] + cognitive[1] + social[1])

    def update_position(self, particle):
        for i in range(n_courses):
            particle.position[i] = (max(0, min(6, particle.position[i][0] + particle.velocity[i][0])), max(0.5, min(3, particle.position[i][1] + particle.velocity[i][1])))

    def run(self):
        for particle in self.swarm:
            particle.evaluate()
            self.update_archive(particle)

        for gen in range(self.max_gen):
            global_best = self.select_global_best()
            for particle in self.swarm:
                self.update_velocity(particle, global_best)
                self.update_position(particle)
                particle.evaluate()
                self.update_archive(particle)

        return list(self.archive)

    def update_archive(self, particle):
        non_dominated = []
        for p in self.archive:
            if particle.dominates(p.objectives):
                continue
            if not p.dominates(particle.objectives):
                non_dominated.append(p)
        non_dominated.append(particle)
        self.archive = deque(non_dominated, maxlen=self.archive.maxlen)

    def select_global_best(self):
        return random.choice(self.archive)

# 运行MOPSO算法
solver = MOPSO(pop_size=50, max_gen=50)
pareto_front = solver.run()

# 显示结果
if not pareto_front:
    print("没有找到有效解，请调整参数或约束条件")
else:
    print("找到的Pareto最优解:")
    for i, particle in enumerate(pareto_front):
        print(f"\n方案 {i + 1}:")
        print(f"总时间: {sum(dur for _, dur in particle.position):.2f}小时")
        print(f"目标值: 时间偏离={particle.objectives[0]:.2f}, 记忆效率={-particle.objectives[1]:.2f}, "
              f"疲劳度={particle.objectives[2]:.2f}, 作业质量={-particle.objectives[3]:.2f}")

        print("作业安排:")
        daily_hours = defaultdict(float)
        for j in range(n_courses):
            day = days[particle.position[j][0]]
            print(f"{courses[j]['name']}: {day}下午, {particle.position[j][1]:.1f}小时")
            daily_hours[day] += particle.position[j][1]

        print("\n每日作业时间分布:")
        for day in days:
            if daily_hours.get(day, 0) > 0:
                print(f"{day}: {daily_hours[day]:.1f}小时")
import random
import math
from collections import defaultdict

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


class Individual:
    def __init__(self):
        self.start_times = [random.randint(0, 6) for _ in range(n_courses)]
        self.durations = [random.uniform(0.5, 3) for _ in range(n_courses)]
        self.objectives = None
        self.rank = None
        self.crowding_distance = None

    def evaluate(self):
        # 目标1: 总时间偏离8小时的程度
        total_time = sum(self.durations)
        f1 = abs(total_time - 8)

        # 目标2: 记忆效率(基于遗忘曲线)
        mem_eff = 0
        for i in range(n_courses):
            delay = self.start_times[i] - courses[i]["day"]
            if delay >= 0:
                mem_eff += courses[i]["credit"] * (0.7 ** delay)

        # 目标3: 疲劳度(基于每日作业时间分布)
        daily_hours = defaultdict(float)
        for day, dur in zip(self.start_times, self.durations):
            daily_hours[day] += dur
        if daily_hours:
            avg = sum(daily_hours.values()) / len(daily_hours)
            f3 = math.sqrt(sum((h - avg) ** 2 for h in daily_hours.values()) / len(daily_hours))
        else:
            f3 = 0

        # 目标4: 作业质量(基于难度和时间分配)
        quality = 0
        for i in range(n_courses):
            quality += min(1, self.durations[i] / courses[i]["difficulty"]) * courses[i]["credit"]

        self.objectives = (f1, -mem_eff, f3, -quality)  # 注意需要最小化的目标


class NSGA2:
    def __init__(self, pop_size=50, max_gen=100):
        self.pop_size = pop_size
        self.max_gen = max_gen

    def run(self):
        population = [Individual() for _ in range(self.pop_size)]
        for ind in population:
            ind.evaluate()

        for gen in range(self.max_gen):
            # 非支配排序
            fronts = self.non_dominated_sort(population)

            # 拥挤度计算
            for front in fronts:
                self.calculate_crowding_distance(front)

            # 选择新一代种群
            new_population = []
            remaining = self.pop_size
            for front in fronts:
                if remaining <= 0:
                    break
                if len(front) <= remaining:
                    new_population.extend(front)
                    remaining -= len(front)
                else:
                    front.sort(key=lambda x: x.crowding_distance, reverse=True)
                    new_population.extend(front[:remaining])
                    remaining = 0

            # 遗传操作
            offspring = self.genetic_operation(new_population)
            for ind in offspring:
                ind.evaluate()

            # 合并种群
            population = new_population + offspring

        # 最终非支配排序
        final_fronts = self.non_dominated_sort(population)
        return final_fronts[0] if final_fronts else []

    def non_dominated_sort(self, population):
        fronts = [[]]
        domination_counts = [0] * len(population)
        dominated_solutions = [[] for _ in range(len(population))]

        # 第一遍计算支配关系
        for i, ind1 in enumerate(population):
            for j in range(i + 1, len(population)):
                ind2 = population[j]
                if self.dominates(ind1, ind2):
                    dominated_solutions[i].append(j)
                    domination_counts[j] += 1
                elif self.dominates(ind2, ind1):
                    dominated_solutions[j].append(i)
                    domination_counts[i] += 1

            if domination_counts[i] == 0:
                ind1.rank = 0
                fronts[0].append(ind1)

        # 构建前沿层级
        current_front = 0
        while fronts[current_front]:
            next_front = []
            for ind in fronts[current_front]:
                idx = population.index(ind)
                for dominated_idx in dominated_solutions[idx]:
                    domination_counts[dominated_idx] -= 1
                    if domination_counts[dominated_idx] == 0:
                        population[dominated_idx].rank = current_front + 1
                        next_front.append(population[dominated_idx])

            current_front += 1
            if next_front:
                fronts.append(next_front)
            else:
                break

        return fronts

    def dominates(self, ind1, ind2):
        """判断ind1是否支配ind2"""
        not_worse = True
        strictly_better = False

        for obj1, obj2 in zip(ind1.objectives, ind2.objectives):
            if obj1 > obj2:  # 对于最小化目标，值越小越好
                not_worse = False
                break
            if obj1 < obj2:
                strictly_better = True

        return not_worse and strictly_better

    def calculate_crowding_distance(self, front):
        if not front:
            return

        num_objs = len(front[0].objectives)
        for ind in front:
            ind.crowding_distance = 0

        for obj_idx in range(num_objs):
            # 按当前目标排序
            front.sort(key=lambda x: x.objectives[obj_idx])

            # 边界个体的拥挤度设为无穷大
            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')

            # 归一化目标值
            min_obj = front[0].objectives[obj_idx]
            max_obj = front[-1].objectives[obj_idx]
            if max_obj == min_obj:
                continue

            # 计算中间个体的拥挤度
            for i in range(1, len(front) - 1):
                distance = (front[i + 1].objectives[obj_idx] - front[i - 1].objectives[obj_idx]) / (max_obj - min_obj)
                front[i].crowding_distance += distance

    def genetic_operation(self, population):
        offspring = []
        while len(offspring) < self.pop_size:
            # 锦标赛选择
            parent1 = self.tournament_selection(population)
            parent2 = self.tournament_selection(population)

            # 交叉
            child1, child2 = self.crossover(parent1, parent2)

            # 变异
            self.mutate(child1)
            self.mutate(child2)

            offspring.append(child1)
            offspring.append(child2)

        return offspring[:self.pop_size]

    def tournament_selection(self, population, k=3):
        selected = random.sample(population, k)
        selected.sort(key=lambda x: (x.rank, -x.crowding_distance))
        return selected[0]

    def crossover(self, parent1, parent2):
        child1 = Individual()
        child2 = Individual()

        # 单点交叉
        cross_point = random.randint(1, n_courses - 1)

        # 交叉开始时间
        child1.start_times = parent1.start_times[:cross_point] + parent2.start_times[cross_point:]
        child2.start_times = parent2.start_times[:cross_point] + parent1.start_times[cross_point:]

        # 交叉持续时间
        cross_point_d = random.randint(1, n_courses - 1)
        child1.durations = parent1.durations[:cross_point_d] + parent2.durations[cross_point_d:]
        child2.durations = parent2.durations[:cross_point_d] + parent1.durations[cross_point_d:]

        return child1, child2

    def mutate(self, individual, mutation_rate=0.1):
        for i in range(n_courses):
            if random.random() < mutation_rate:
                individual.start_times[i] = random.randint(0, 6)
            if random.random() < mutation_rate:
                individual.durations[i] = random.uniform(0.5, 3)


# 运行算法
solver = NSGA2(pop_size=50, max_gen=50)
pareto_front = solver.run()

# 显示结果
if not pareto_front:
    print("没有找到有效解，请调整参数或约束条件")
else:
    print("找到的Pareto最优解:")
    for i, ind in enumerate(pareto_front):
        print(f"\n方案 {i + 1}:")
        print(f"总时间: {sum(ind.durations):.2f}小时")
        print(f"目标值: 时间偏离={ind.objectives[0]:.2f}, 记忆效率={-ind.objectives[1]:.2f}, "
              f"疲劳度={ind.objectives[2]:.2f}, 作业质量={-ind.objectives[3]:.2f}")

        print("作业安排:")
        daily_hours = defaultdict(float)
        for j in range(n_courses):
            day = days[ind.start_times[j]]
            print(f"{courses[j]['name']}: {day}下午, {ind.durations[j]:.1f}小时")
            daily_hours[day] += ind.durations[j]

        print("\n每日作业时间分布:")
        for day in days:
            if daily_hours.get(day, 0) > 0:
                print(f"{day}: {daily_hours[day]:.1f}小时")
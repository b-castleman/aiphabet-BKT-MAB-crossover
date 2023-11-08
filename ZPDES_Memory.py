import json
import time
import random
import copy
import memory
import math
import numpy as np

current_time = lambda: int(round(time.time() * 100))

DEFAULT_PARAMS = {
            #Must be defined
            'history_length': 2,
            'progress_threshold': 0.49,
            'memory_threshold': math.exp(-18),
            'memory_multiplier': 1000000,
            
            #Optional
            'skip': 2, #defaults to history length
            'min_concept_attempts': 4, #defaults to history_length + skip
            'max_concept_attempts': math.inf, #some really large value
            'min_weight': 0.001, #some really small non-zero value for purposes of avoiding dividing by zero
            'gamma': 0.1, #Default
            'initial_weight': 0.5, #Default
            'initial_weight_multiplier': 4, #Default
            }

class ZPDES_Memory(object):

    def __init__(self, progression_tree, params = DEFAULT_PARAMS):
        #print("test")
        
        #Load in the tree
        self.progression_tree = progression_tree
        all_concepts_list = self.progression_tree.return_all_concepts()
        all_components_list = self.progression_tree.return_all_basic_components()
        
        #ZPDES parameters
        self.params = params
        #check params are there:
        assert 'history_length' in params, "history_length is not defined"
        assert 'progress_threshold' in params, "progress_threshold is not defined"
        assert 'memory_threshold' in params, "memory_threshold is not defined"
        assert 'memory_multiplier' in params, "memory_multiplier is not defined"

        if 'skip' not in self.params:
        	self.params['skip'] = self.params['history_length']
        if 'min_concept_attempts' not in self.params:
        	self.params['min_concept_attempts'] = self.params['history_length'] + self.params['skip']
        if 'max_concept_attempts' not in self.params:
        	self.params['max_concept_attempts'] = DEFAULT_PARAMS['max_concept_attempts']
        if 'min_weight' not in self.params:
        	self.params['min_weight'] = DEFAULT_PARAMS['min_weight']
        if 'gamma' not in self.params:
        	self.params['gamma'] = DEFAULT_PARAMS['gamma']
        if 'initial_weight' not in self.params:
        	self.params['initial_weight'] = DEFAULT_PARAMS['initial_weight']
        if 'initial_weight_multiplier' not in self.params:
        	self.params['initial_weight_multiplier'] = DEFAULT_PARAMS['initial_weight_multiplier']

        self.concept_problems = self.progression_tree.return_concept_problems()
        self.problem_components = self.progression_tree.return_problem_components()

        self.all_prereqs = self.progression_tree.return_all_ancestors()
        self.prereqs = self.progression_tree.return_parents()
        #print("Self prereqs:",self.prereqs)
        self.children = self.progression_tree.return_children()
        
        self.weights = {node:self.params['initial_weight'] for node in all_concepts_list}
        self.weights_histories = {node:[self.params['initial_weight'], self.params['initial_weight']] for node in all_concepts_list}
        self.correctnesses = {node:[] for node in all_concepts_list}
        self.mastered_concepts = [] #which concepts are mastered
        
        self.ZPD = [node for node in all_concepts_list if len(self.prereqs[node]) == 0]
        random.shuffle(self.ZPD)
        self.length_ZPD = len(self.ZPD)

        self.concept = None
        self.problem = None
        self.attempts = 0
        self.last_problem = None
        
        #Memory Variables
        self.memory_concept = None

        #set the next three variables to None if want to turn off memory
        self.memory_type = memory.MEMORY_TYPES.MCM_AVERAGE
        self.time_type = memory.TIME_TYPES.DISCRETE
        self.review_type = memory.REVIEW_TYPES.AS_NECESSARY
        #self.memory_type = None
        #self.time_type = None
        #self.review_type = None
        
        self.begin_continuous_time = current_time()
        self.discrete_time = 0

        self.concepts_seen_history = {node:[] for node in all_concepts_list}
        self.concepts_memory = {node:10000 for node in all_concepts_list}
        self.components_seen_history = {component:[] for component in all_components_list}
        self.components_memory = {component:0.0001 for component in all_components_list}
        
        #Data Variables:
        self.problems_history = []
        self.answers_history = []
        
        #Get a new problem
        self.new_problem()

        #print("Current problem:",self.problem)

    def get_current_time(self):
        return current_time() - self.begin_time

    def new_problem(self):
        self.attempts = 0
        if self.length_ZPD == 0:
            self.memory_concept = None
            self.problem = None
            self.concept = None
        else:
    		#CHOOSE CONCEPT
            self.calculate_concepts_memory()
            if self.memory_concept == None:
                length_ZPD = self.length_ZPD
                weights_ZPD = np.zeros(length_ZPD)
                zeta = np.ones(length_ZPD) / float(length_ZPD)
                gamma = self.params['gamma']

                weights_sum = 0
                for idx, concept in enumerate(self.ZPD):
                    if len(self.weights_histories[concept]) > 2:
                        mean_weight = np.mean(self.weights_histories[concept][1:])
                    else:
                        mean_weight = np.mean(self.weights_histories[concept])
                    self.weights[concept] = max(mean_weight, self.params['min_weight'])
                    weights_ZPD[idx] = self.weights[concept]
                    weights_sum += weights_ZPD[idx]

                #add exploration in
                weights_ZPD = weights_ZPD + (float(weights_sum) * gamma/( 1.0 - gamma )) * zeta
                weights_sum += weights_sum * gamma/float( 1.0 - gamma)
                concepts_selection = copy.deepcopy(self.ZPD)

                

                #if we are accounting for memory by adding it into the concepts ZPDES should select from
                if self.review_type == memory.REVIEW_TYPES.IN_PROGRESSION:
                    memory_threshold = self.params['memory_threshold']
                    memory_multiplier = self.params['memory_multiplier']

                    weights_memory = np.zeros(len(self.mastered_concepts))
                    for idx, item in enumerate(self.mastered_concepts):
                        weights_memory[idx] = memory_multiplier * max(memory_threshold - self.concepts_memory[item], 0)
                        weights_sum += weights_memory[idx]

                    weights_ZPD = np.hstack([weights_ZPD, weights_memory])
                    concepts_selection = list(concepts_selection) + self.mastered_concepts

                #select concept
                pa = weights_ZPD / float(weights_sum)
                #print("Concept Selection:")
                #print(concepts_selection)
                #print(pa)
                self.concept = np.random.choice(concepts_selection, 1, p=pa)[0]

            if self.review_type == memory.REVIEW_TYPES.AS_NECESSARY:
                memory_threshold = self.params['memory_threshold']
                self.memory_concept = None
                for key in self.prereqs[self.concept]:
                    if (self.concepts_memory[key] < memory_threshold) and (key not in self.ZPD):
                        self.memory_concept = key
                        break
            
            #SET PROBLEM
            self.set_problem()
        
    def set_problem(self):
        concept = self.memory_concept
        if concept == None:
            concept = self.concept
        #print("ZPD:",self.ZPD)
        #print("Memory concept:",self.concept)

        concept_problems = copy.deepcopy(self.concept_problems[concept])
        if len(concept_problems) > 1 and self.last_problem in concept_problems:
            concept_problems.remove(self.last_problem)
        problem_scores = np.zeros(len(concept_problems))
        #print("Problem Picker!! Begin!")
        #print("Concept problems: v v v")
        #print(concept_problems)
        for idx, problem in enumerate(concept_problems):
            problem_components = self.problem_components[problem]
            for component in problem_components:
                problem_scores[idx] += 1.0/self.components_memory[component]
                #print('Component:',component)
                #print('Score:',problem_scores[idx])
        #print(problem_scores)
        #print(concept_problems)
        max_problem_arg = np.argmax(problem_scores)
        self.problem = concept_problems[max_problem_arg]
        #print("Problem is now picked.")

    def student_attempt_update(self, student_attempt_correctness):
        if student_attempt_correctness:
            self.student_answer_update(self.attempts == 0)
        else:
            self.discrete_time += 1
            self.attempts += 1
            
    def student_answer_update(self, student_answer_correctness):
        self.discrete_time += 1
        if not student_answer_correctness:
            self.attempts = max(1, self.attempts)
        self.answers_history.append(self.attempts)
        self.problems_history.append(self.problem)
        self.last_problem = self.problem

        #if not self.learning_mode and student_answer_correctness:
        if student_answer_correctness:
            self.update_memories()

        if self.memory_concept is None and self.concept in self.ZPD: #If not reviewing
            history_length = self.params['history_length']
            skip = self.params['skip']
            min_concept_attempts = self.params['min_concept_attempts']
            progress_threshold = self.params['progress_threshold']
            max_concept_attemtps = self.params['max_concept_attempts']
            concept = self.concept

            self.correctnesses[concept].append(student_answer_correctness)
            num_concept_attempts = len(self.correctnesses[concept])
            if num_concept_attempts >= history_length + skip:
                reward = sum(self.correctnesses[concept][num_concept_attempts - history_length:]) / float(history_length) - sum(self.correctnesses[concept][num_concept_attempts - history_length - skip:num_concept_attempts - skip]) / float(history_length)
                self.weights_histories[concept].append(reward)
            if (len(self.correctnesses[concept]) >= min_concept_attempts and sum(self.correctnesses[concept][-min_concept_attempts:]) / float(min_concept_attempts) >= progress_threshold) or len(self.correctnesses[concept]) >= max_concept_attemtps:
                self.ZPD.remove(concept)
                self.mastered_concepts.append(concept)

                initial_weight = self.params['initial_weight']*self.params['initial_weight_multiplier']
                for child in self.children[concept]:
                    can_add = True
                    for prereq in self.prereqs[child]:
                        if prereq not in self.mastered_concepts:
                            can_add = False

                    if can_add:
                        self.ZPD.append(child)
                        self.weights_histories[child][0] = initial_weight

            self.length_ZPD = len(self.ZPD)

        self.new_problem()

    def update_memories(self):
        if self.time_type == memory.TIME_TYPES.CONTINUOUS:
            current_time_stamp = self.get_current_time()
        else:
            current_time_stamp = self.discrete_time

        concept_key = self.memory_concept
        if concept_key == None:
            concept_key = self.concept

        #add time reviewed in current_time_stamp and those of concepts easier than it
        self.concepts_seen_history[concept_key].append(current_time_stamp)
        for key in self.all_prereqs[concept_key]:
            self.concepts_seen_history[key].append(current_time_stamp)
        
        #add time reviewed for the problem components
        problem_components = self.problem_components[self.problem]
        for problem_component in problem_components:
            self.components_seen_history[problem_component].append(current_time_stamp)

    def calculate_concepts_memory(self):
        if self.time_type == memory.TIME_TYPES.CONTINUOUS:
            current_time_stamp = self.get_current_time()
        else:
            current_time_stamp = self.discrete_time

        self.concepts_memory = memory.get_memory_strengths(self.memory_type, self.concepts_seen_history, current_time_stamp, memory_multiplier = self.params['memory_multiplier'], base_memory = 10000)
        self.components_memory = memory.get_memory_strengths(self.memory_type, self.components_seen_history, current_time_stamp, memory_multiplier = self.params['memory_multiplier'], base_memory = 0.0001)
    
    def get_current_problem(self):
        return self.problem
            
    def get_progression_student_info(self):
        return (self.problems_history, self.answers_history)